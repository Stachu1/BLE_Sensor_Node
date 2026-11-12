#!/usr/bin/env python3
"""
bsn_scan_nina.py - bsn_scan.py, but receiving through a u-blox NINA-W15 (u-connectXpress) on a COM port.

    pip install pyserial bleak               # bleak only because the decoder is imported from bsn_scan.py
    python bsn_scan_nina.py                  # every BTHome device named BSN-*, NINA on COM9
    python bsn_scan_nina.py --port COM5 --mac AA:BB:CC:DD:EE:FF
    python bsn_scan_nina.py --all            # print every advertisement, not just new packet ids
    python bsn_scan_nina.py --csv log.csv    # also append decoded readings to a CSV file (same columns as bsn_scan.py)
    python bsn_scan_nina.py --setup          # one time: enable Bluetooth LE (central) on the module, save, restart

The module cannot scan continuously. AT+UBTD runs one discovery window (at most 40 s), so the
script starts a new window as soon as the module reports the last one finished (the gap is a few
tens of ms). Prints one line per new reading (BTHome packet id), with RSSI. Stop with Ctrl+C.
"""
import argparse
import csv
import datetime as dt
import sys
import time

import serial

from bsn_scan import decode_bthome

BTHOME_UUID16 = 0xFCD2
AD_NAME_SHORT = 0x08
AD_NAME_COMPLETE = 0x09
AD_SERVICE_DATA_16 = 0x16

MAX_WINDOW_S = 40.0  # u-connectXpress limit for AT+UBTD discovery_length (40000 ms)


def parse_ad(data: bytes) -> tuple[str | None, bytes | None]:
    """Returns (local name, BTHome service data) from raw advertising data AD structures."""
    name, bthome = None, None
    i = 0
    while i < len(data):
        length = data[i]
        if length == 0 or i + 1 + length > len(data):
            break
        ad_type, value = data[i + 1], data[i + 2 : i + 1 + length]
        if ad_type in (AD_NAME_SHORT, AD_NAME_COMPLETE):
            name = value.decode("utf-8", errors="replace")
        elif ad_type == AD_SERVICE_DATA_16 and len(value) >= 2 and int.from_bytes(value[:2], "little") == BTHOME_UUID16:
            bthome = value[2:]
        i += 1 + length
    return name, bthome


def parse_ubtd(line: str):
    """+UBTD:<bd_addr>,<rssi>,"<name>",<data_type>,<hex data> -> (addr, rssi, name, data_type, bytes)."""
    body = line[len("+UBTD:"):]
    addr_raw, rssi, rest = body.split(",", 2)
    name_end = rest.rindex('"')  # the name is quoted and may itself contain commas
    name = rest[1:name_end]
    data_type, hexdata = rest[name_end + 2 :].split(",", 1)
    addr_raw = addr_raw.rstrip("prPR")  # trailing p = public, r = random address
    addr = ":".join(addr_raw[i : i + 2] for i in range(0, 12, 2)).upper()
    return addr, int(rssi), name, int(data_type), bytes.fromhex(hexdata) if hexdata else b""


class Nina:
    def __init__(self, port: str, baud: int):
        self.ser = serial.Serial(port, baud, timeout=0.1)
        self.buf = b""

    def readline(self) -> str | None:
        """One response line, or None if nothing arrived within the serial timeout."""
        while b"\r\n" not in self.buf:
            chunk = self.ser.read(4096)
            if not chunk:
                return None
            self.buf += chunk
        line, self.buf = self.buf.split(b"\r\n", 1)
        return line.decode("ascii", errors="replace").strip()

    def send(self, cmd: str) -> None:
        self.ser.write((cmd + "\r").encode())

    def command(self, cmd: str, timeout: float = 2.0) -> list[str]:
        """Sends a command and returns the lines up to OK. Raises on ERROR or timeout.
        Leftover +UBTD lines from a scan that was still running are dropped."""
        self.send(cmd)
        out, t_end = [], time.monotonic() + timeout
        while time.monotonic() < t_end:
            line = self.readline()
            if line is None or line == "" or line.startswith("+UBTD:") or line == cmd:
                continue
            if line == "OK":
                return out
            if line == "ERROR":
                raise RuntimeError(f"{cmd} -> ERROR")
            out.append(line)
        raise TimeoutError(f"{cmd}: no OK within {timeout:.0f} s")

    def sync(self) -> None:
        """Waits until the module is idle. A scan left running by an earlier run (Ctrl+C) holds
        commands until it ends (up to 40 s) and its own OK can arrive first, so drain and ask again."""
        self.command("AT", timeout=MAX_WINDOW_S + 5)
        time.sleep(0.3)
        self.ser.reset_input_buffer()
        self.buf = b""
        self.command("AT")

    def reopen(self) -> None:
        """Reopens the port after the USB serial device dropped out, retrying every second."""
        try:
            self.ser.close()
        except serial.SerialException:
            pass
        while True:
            time.sleep(1)
            try:
                self.ser.open()
                self.buf = b""
                self.sync()
                return
            except (serial.SerialException, TimeoutError, RuntimeError):
                try:
                    self.ser.close()
                except serial.SerialException:
                    pass

    def close(self) -> None:
        self.ser.close()


def setup(nina: Nina) -> None:
    """Enables Bluetooth LE central on the module, stores it and restarts the module."""
    nina.command("AT+UBTLE=1")
    nina.command("AT&W")
    nina.command("AT+CPWROFF")
    t_end = time.monotonic() + 10
    while time.monotonic() < t_end and nina.readline() != "+STARTUP":
        pass
    time.sleep(0.5)
    print("Module:", " ".join(nina.command("AT+UBTLE?")), "(1 = central, Bluetooth LE on)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default="COM9", help="NINA-W15 serial port (default: COM9)")
    ap.add_argument("--baud", type=int, default=115200, help="module baud rate (default: 115200)")
    ap.add_argument("--window", type=float, default=15, help=f"discovery window in s, max {MAX_WINDOW_S:.0f} (default: 15)")
    ap.add_argument("--active", action="store_true", help="active scanning (default: passive, the BSN puts everything in the advert)")
    ap.add_argument("--mac", help="only this device address (case and separators don't matter)")
    ap.add_argument("--name", default="BSN-", help="name prefix filter when --mac is not given (default: BSN-)")
    ap.add_argument("--all", action="store_true", help="print every advertisement, including repeats")
    ap.add_argument("--csv", help="append decoded readings to this CSV file")
    ap.add_argument("--time", type=float, default=0, help="stop after this many seconds (default: run until Ctrl+C)")
    ap.add_argument("--verbose", action="store_true", help="also print the start of every discovery window")
    ap.add_argument("--setup", action="store_true", help="enable Bluetooth LE on the module (stored in flash), then exit")
    args = ap.parse_args()

    if not 0.01 <= args.window <= MAX_WINDOW_S:
        ap.error(f"--window must be between 0.01 and {MAX_WINDOW_S:.0f} s")

    nina = Nina(args.port, args.baud)
    print(f"Connecting to the module on {args.port} ...", flush=True)
    nina.sync()
    if args.setup:
        setup(nina)
        nina.close()
        return
    if "+UBTLE:0" in nina.command("AT+UBTLE?"):
        sys.exit("Bluetooth LE is disabled on the module (+UBTLE:0). Run once with --setup.")

    want_mac = args.mac.replace("-", ":").upper() if args.mac else None
    names: dict[str, str] = {}  # address -> name, the name can come from the advert or a scan response
    last_packet: dict[str, int] = {}
    seen_any = False
    windows = 0
    csv_file = open(args.csv, "a", newline="") if args.csv else None
    writer = csv.writer(csv_file) if csv_file else None
    mode = 1 if args.active else 2

    def on_adv(addr: str, rssi: int, name: str, data: bytes) -> None:
        nonlocal seen_any
        ad_name, payload = parse_ad(data)
        if ad_name or name:
            names[addr] = ad_name or name
        local_name = names.get(addr, "")
        if want_mac:
            if addr != want_mac:
                return
        elif not local_name.startswith(args.name) or payload is None:
            return

        values = decode_bthome(payload) if payload else {"error": "no BTHome service data"}
        pkt = values.get("packet")
        if not args.all and pkt is not None and last_packet.get(addr) == pkt:
            return
        last_packet[addr] = pkt
        seen_any = True

        now = dt.datetime.now().strftime("%H:%M:%S")
        fields = "  ".join(f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}" for k, v in values.items())
        print(f"{now}  {addr}  {local_name or '?':10s} RSSI {rssi:4d} dBm  {fields}", flush=True)
        if writer and "error" not in values:
            writer.writerow([dt.datetime.now().isoformat(timespec="seconds"), addr, rssi,
                             values.get("packet"), values.get("temp_C"), values.get("rh_pct"),
                             values.get("vdd_V"), values.get("battery_pct")])
            csv_file.flush()

    def scan_window(cmd: str, window: float) -> None:
        """Runs one discovery window and returns when the module reports it finished."""
        nonlocal windows
        nina.send(cmd)
        windows += 1
        if args.verbose:
            print(f"{dt.datetime.now():%H:%M:%S}  -- window {windows} ({window:.1f} s)", flush=True)
        t_end = time.monotonic() + window + 5
        while True:
            line = nina.readline()
            if line is None:
                if time.monotonic() > t_end:
                    print("No end of window from the module, restarting the scan.", file=sys.stderr, flush=True)
                    return
                continue
            if line.startswith("+UBTD:"):
                try:
                    addr, rssi, name, _, data = parse_ubtd(line)
                except ValueError:
                    continue  # truncated or garbled line
                on_adv(addr, rssi, name, data)
            elif line == "OK":
                return
            elif line == "ERROR":
                print(f"{cmd} -> ERROR, retrying in 1 s", file=sys.stderr, flush=True)
                time.sleep(1)
                return
            elif line == "+STARTUP":
                print("Module restarted, restarting the scan.", file=sys.stderr, flush=True)
                time.sleep(0.5)
                return

    target = want_mac or f"name starting with '{args.name}'"
    print(f"Scanning for {target} through the NINA, {args.window:g} s windows ... (Ctrl+C to stop)", flush=True)
    t_stop = time.monotonic() + args.time if args.time else None
    try:
        while True:
            window = args.window
            if t_stop is not None:
                left = t_stop - time.monotonic()
                if left < 0.01:
                    break
                window = min(window, left)
            cmd = f"AT+UBTD=1,{mode},{round(window * 1000)}"
            try:
                scan_window(cmd, window)
            except serial.SerialException as e:
                print(f"{dt.datetime.now():%H:%M:%S}  Lost {args.port} ({e}), reopening ...", file=sys.stderr, flush=True)
                nina.reopen()
                print(f"{dt.datetime.now():%H:%M:%S}  {args.port} back, scanning again.", file=sys.stderr, flush=True)
    finally:
        if csv_file:
            csv_file.close()
        nina.close()
    if not seen_any:
        print("No matching advertisements received.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

#!/usr/bin/env python3
"""
bsn_scan.py - listen for BSN sensor-node advertisements and decode the BTHome v2 payload.

    pip install bleak
    python bsn_scan.py                       # every BTHome device named BSN-*
    python bsn_scan.py --mac AA:BB:CC:DD:EE:FF
    python bsn_scan.py --all                 # print every advertisement, not just new packet ids
    python bsn_scan.py --csv log.csv         # also append decoded readings to a CSV file

Prints one line per new reading (BTHome packet id), with RSSI. Stop with Ctrl+C.
"""
import argparse
import asyncio
import csv
import datetime as dt
import struct

from bleak import BleakScanner

BTHOME_UUID = "0000fcd2-0000-1000-8000-00805f9b34fb"

# BTHome v2 object id -> (name, struct format, scale), see https://bthome.io/format/
OBJECTS = {
    0x00: ("packet", "<B", 1),
    0x01: ("battery_pct", "<B", 1),
    0x02: ("temp_C", "<h", 0.01),
    0x03: ("rh_pct", "<H", 0.01),
    0x0C: ("vdd_V", "<H", 0.001),
}


def decode_bthome(data: bytes) -> dict:
    """Decodes unencrypted BTHome v2 service data. Stops at the first unknown object id."""
    if not data or data[0] & 0x01:
        return {"error": "encrypted or empty"}
    if (data[0] >> 5) != 2:
        return {"error": f"not BTHome v2 (device info 0x{data[0]:02X})"}
    out, i = {}, 1
    while i < len(data):
        oid = data[i]
        if oid not in OBJECTS:
            out["unknown_object"] = f"0x{oid:02X}"
            break
        name, fmt, scale = OBJECTS[oid]
        size = struct.calcsize(fmt)
        (raw,) = struct.unpack_from(fmt, data, i + 1)
        out[name] = raw * scale if scale != 1 else raw
        i += 1 + size
    return out


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mac", help="only this device address (case and separators don't matter)")
    ap.add_argument("--name", default="BSN-", help="name prefix filter when --mac is not given (default: BSN-)")
    ap.add_argument("--all", action="store_true", help="print every advertisement, including repeats")
    ap.add_argument("--csv", help="append decoded readings to this CSV file")
    ap.add_argument("--time", type=float, default=0, help="stop after this many seconds (default: run until Ctrl+C)")
    args = ap.parse_args()

    want_mac = args.mac.replace("-", ":").upper() if args.mac else None
    last_packet: dict[str, int] = {}
    seen_any = False
    csv_file = open(args.csv, "a", newline="") if args.csv else None
    writer = csv.writer(csv_file) if csv_file else None

    def on_adv(device, adv):
        nonlocal seen_any
        addr = device.address.upper()
        if want_mac:
            if addr != want_mac:
                return
        elif not (adv.local_name or "").startswith(args.name) or BTHOME_UUID not in adv.service_data:
            return

        payload = adv.service_data.get(BTHOME_UUID)
        values = decode_bthome(payload) if payload else {"error": "no BTHome service data"}
        pkt = values.get("packet")
        if not args.all and pkt is not None and last_packet.get(addr) == pkt:
            return
        last_packet[addr] = pkt
        seen_any = True

        now = dt.datetime.now().strftime("%H:%M:%S")
        fields = "  ".join(
            f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}" for k, v in values.items()
        )
        print(f"{now}  {addr}  {adv.local_name or '?':10s} RSSI {adv.rssi:4d} dBm  {fields}", flush=True)
        if writer and "error" not in values:
            writer.writerow([dt.datetime.now().isoformat(timespec="seconds"), addr, adv.rssi,
                             values.get("packet"), values.get("temp_C"), values.get("rh_pct"),
                             values.get("vdd_V"), values.get("battery_pct")])
            csv_file.flush()

    target = want_mac or f"name starting with '{args.name}'"
    print(f"Scanning for {target} ... (Ctrl+C to stop)", flush=True)
    async with BleakScanner(detection_callback=on_adv):
        try:
            if args.time:
                await asyncio.sleep(args.time)
            else:
                while True:
                    await asyncio.sleep(1)
        finally:
            if csv_file:
                csv_file.close()
    if not seen_any:
        print("No matching advertisements received.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

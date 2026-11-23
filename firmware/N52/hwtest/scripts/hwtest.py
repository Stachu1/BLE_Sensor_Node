"""Host side of the BSN-N52 hwtest and general flash tool, for a SEGGER J-Link or an ST-Link.

    python hwtest.py soc              does the SoC answer on SWD? (DAP ID, FICR part/RAM/flash, UICR, BLE address)
    python hwtest.py flash [hex]      program + verify + reset (default ../build/zephyr/zephyr.hex)
    python hwtest.py report           read the hwtest result struct out of RAM and print it
    python hwtest.py run [hex]        flash, wait for the tests, print the report

    --probe jlink|stlink   which probe (default: env HWTEST_PROBE, else jlink)
    --uid <serial>         pick one probe when several are connected (stlink only)

J-Link  : uses JLink.exe from the SEGGER install, nothing else to install. JLINK_EXE overrides the path,
          JLINK_SPEED the SWD speed in kHz (default 2000).
ST-Link : uses pyocd (python -m pip install pyocd). NOT TESTED YET on this board (the J-Link path is).
The hwtest result struct address comes from zephyr.elf (symbol hwtest_report).
"""
import argparse
import glob
import os
import re
import struct
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FW_ROOT = os.path.join(HERE, "..")
NM = r"C:\ncs\toolchains\dcbdc366a1\opt\zephyr-sdk\gnu\arm-zephyr-eabi\bin\arm-zephyr-eabi-nm.exe"
MAGIC = 0x48575453
NAMES = ["SoC identity (FICR)", "VDD rail (SAADC)", "32 MHz crystal", "SDA/SCL/INT pin shorts", "I2C bus scan",
         "HDC2010 ID", "HDC2010 measurement", "INT line: data ready", "INT line: thresholds",
         "DC/DC converter", "Radio / BLE"]
STATUS = {0: "----", 1: "PASS", 2: "FAIL", 3: "SKIP"}

FICR_INFO = 0x10000100       # PART, VARIANT, PACKAGE, RAM, FLASH
FICR_DEVICEID = 0x10000060   # 2 words
FICR_ADDRTYPE = 0x100000A0   # 1 word, bit 0 = random
FICR_DEVICEADDR = 0x100000A4  # 2 words
UICR_PSELRESET = 0x10001200  # 2 words
UICR_APPROTECT = 0x10001208


# --------------------------------------------------------------------------------------------------------------
# Probe backends. run(actions) does all actions in one connection and returns a dict with "reads" (one entry per
# read action, in order), "info", "dpidr" and, when flashing, "flash_ok".
# Actions: ("words", addr, n) ("bytes", addr, n) ("flash", hexfile) ("reset_run",) ("wait", s) ("halt",)
# --------------------------------------------------------------------------------------------------------------
class JLink:
    name = "J-Link"

    def __init__(self, uid=None):
        self.uid = uid

    @staticmethod
    def exe():
        if os.environ.get("JLINK_EXE"):
            return os.environ["JLINK_EXE"]
        found = sorted(glob.glob(r"C:\Program Files\SEGGER\JLink*\JLink.exe"))
        if not found:
            sys.exit("JLink.exe not found (set JLINK_EXE)")
        return found[-1]

    def run(self, actions):
        cmds, reads = ["connect"], []
        for kind, *arg in actions:
            if kind == "words":
                cmds.append(f"mem32 0x{arg[0]:x} {arg[1]}")
                reads.append(("w", arg[0], arg[1]))
            elif kind == "bytes":
                cmds.append(f"mem8 0x{arg[0]:x} {arg[1]}")
                reads.append(("b", arg[0], arg[1]))
            elif kind == "flash":
                cmds += ["r", "h", "loadfile " + arg[0].replace("\\", "/")]
            elif kind == "reset_run":
                cmds += ["r", "g"]
            elif kind == "wait":
                cmds.append(f"sleep {int(arg[0] * 1000)}")
            elif kind == "halt":
                cmds.append("h")
        cmds.append("g")  # leave the target running
        with tempfile.NamedTemporaryFile("w", suffix=".jlink", delete=False) as f:
            f.write("\n".join(cmds + ["exit"]))
        try:
            out = subprocess.run(
                [self.exe(), "-device", "nRF52805_xxAA", "-if", "SWD", "-speed", os.environ.get("JLINK_SPEED", "2000"),
                 "-autoconnect", "1", "-NoGui", "1", "-ExitOnError", "1", "-CommandFile", f.name],
                capture_output=True, text=True, timeout=180).stdout
        finally:
            os.unlink(f.name)
        if "Cortex-M4 identified" not in out:
            print(out[-1500:])
            sys.exit("could not connect (J-Link plugged in, board powered, SWD wired?)")
        words, byts = {}, {}
        for m in re.finditer(r"^([0-9A-F]{8}) = ((?:[0-9A-F]{8} ?)+)", out, re.M):
            for i, w in enumerate(m.group(2).split()):
                words[int(m.group(1), 16) + 4 * i] = int(w, 16)
        for m in re.finditer(r"^([0-9A-F]{8}) = ((?:[0-9A-F]{2} ?)+)$", out, re.M):
            for i, w in enumerate(m.group(2).split()):
                byts[int(m.group(1), 16) + i] = int(w, 16)
        res = {"reads": []}
        for kind, addr, n in reads:
            res["reads"].append([words[addr + 4 * i] for i in range(n)] if kind == "w"
                                else [byts[addr + i] for i in range(n)])
        sn = re.search(r"S/N: (\d+)", out)
        vt = re.search(r"VTref=([\d.]+)V", out)
        res["info"] = "S/N %s  VTref %s V" % (sn.group(1) if sn else "?", vt.group(1) if vt else "?")
        dp = re.search(r"DPIDR: (0x\w+)", out)
        res["dpidr"] = dp.group(1) if dp else "n/a"
        if any(a[0] == "flash" for a in actions):
            res["flash_ok"] = "O.K." in out and not re.search(r"^(ERROR|.*(Failed to|download failed))", out,
                                                              re.M | re.I)
        return res


class PyOcd:
    """ST-Link through pyocd (a J-Link or CMSIS-DAP would work too). Untested on this board."""
    name = "ST-Link (pyocd)"

    def __init__(self, uid=None):
        self.uid = uid

    def run(self, actions):
        try:
            from pyocd.core.helpers import ConnectHelper
            from pyocd.flash.file_programmer import FileProgrammer
        except ImportError:
            sys.exit("pyocd missing: python -m pip install pyocd")
        sess = ConnectHelper.session_with_chosen_probe(
            unique_id=self.uid, target_override="nrf52", blocking=False,
            options={"frequency": 2000000, "auto_unlock": False, "connect_mode": "halt"})
        if sess is None:
            sys.exit("no ST-Link found (plugged in? drivers?). `python -m pyocd list` shows the probes")
        res = {"reads": []}
        with sess:
            t = sess.target
            res["info"] = "%s  uid %s" % (sess.probe.product_name, sess.probe.unique_id)
            try:
                res["dpidr"] = "0x%08X" % t.dp.dpidr.idr
            except Exception:
                res["dpidr"] = "n/a"
            for kind, *arg in actions:
                if kind == "words":
                    res["reads"].append([t.read32(arg[0] + 4 * i) for i in range(arg[1])])
                elif kind == "bytes":
                    res["reads"].append(list(t.read_memory_block8(arg[0], arg[1])))
                elif kind == "flash":
                    FileProgrammer(sess, smart_flash=True).program(arg[0], file_format="hex")
                    res["flash_ok"] = True
                elif kind == "reset_run":
                    t.reset()
                elif kind == "wait":
                    time.sleep(arg[0])
                elif kind == "halt":
                    t.halt()
            t.resume()
        return res


def make_probe(args):
    name = (args.probe or os.environ.get("HWTEST_PROBE") or "jlink").lower()
    if name in ("jlink", "j-link"):
        return JLink(args.uid)
    if name in ("stlink", "st-link", "pyocd"):
        return PyOcd(args.uid)
    sys.exit("--probe must be jlink or stlink")


# --------------------------------------------------------------------------------------------------------------
def ble_address(addrtype, a0, a1):
    """Expected BLE identity address: FICR DEVICEADDR with the top two bits set (static random, as Zephyr does)."""
    raw = bytearray(struct.pack("<II", a0, a1)[:6])
    if addrtype & 1:
        raw[5] |= 0xC0
    return ":".join("%02X" % b for b in reversed(raw))


def cmd_soc(probe):
    r = probe.run([("words", FICR_INFO, 5), ("words", FICR_DEVICEID, 2), ("words", UICR_PSELRESET, 2),
                   ("words", UICR_APPROTECT, 1), ("words", FICR_ADDRTYPE, 1), ("words", FICR_DEVICEADDR, 2)])
    (part, var, pkg, ram, flash), dev, ps, ap, at, da = r["reads"]
    print(f"probe      : {probe.name}  {r['info']}")
    print(f"DAP        : {r['dpidr']}  (Cortex-M4 DAP = 0x2BA01477)")
    print(f"FICR       : part nRF{part:x}  variant {struct.pack('>I', var).decode('latin1')}  package 0x{pkg:x}  "
          f"RAM {ram} kB  flash {flash} kB")
    print(f"device id  : {dev[1]:08x}{dev[0]:08x}")
    print(f"BLE address: {ble_address(at[0], da[0], da[1])}  (expected identity address of ble_sensor)")
    print(f"UICR       : PSELRESET {ps[0]:08x} {ps[1]:08x} (reset pin P0.21 = 00000015)  "
          f"APPROTECT {ap[0]:08x} (FFFFFFFF = open)")
    ok = part == 0x52805 and ram == 24 and flash == 192
    print("RESULT     :", "PASS - the nRF52805 answers" if ok else "FAIL - wrong or unreadable part")
    return 0 if ok else 1


def default_hex():
    return os.path.abspath(os.path.join(FW_ROOT, "build", "zephyr", "zephyr.hex"))


def cmd_flash(probe, hexf=None):
    hexf = os.path.abspath(hexf or default_hex())
    if not os.path.exists(hexf):
        sys.exit(f"{hexf} not found - build first (make in firmware/N52/hwtest)")
    r = probe.run([("flash", hexf), ("reset_run",)])
    ok = r.get("flash_ok")
    print("flash", "OK" if ok else "FAILED", "-", hexf)
    return 0 if ok else 1


def symbol(name, elf):
    for line in subprocess.check_output([NM, elf], text=True).splitlines():
        p = line.split()
        if len(p) == 3 and p[2] == name:
            return int(p[0], 16)
    sys.exit(f"symbol {name} not found in {elf}")


def cmd_report(probe, wait_s=0):
    # the report layout belongs to the hwtest build, always take its elf
    a = symbol("hwtest_report", os.path.join(FW_ROOT, "build", "zephyr", "zephyr.elf"))
    acts = []
    if wait_s:
        acts += [("reset_run",), ("wait", wait_s)]
    acts += [("halt",), ("words", a, 4), ("bytes", a + 16, 16), ("words", a + 32, 66)]
    r = probe.run(acts)
    (magic, ver, done, rr), st, vals = r["reads"]
    if magic != MAGIC or not done:
        print("tests have not finished (no report in RAM) - use `run`, or wait a few seconds")
        return 1
    print(f"reset reason 0x{rr:x}")
    fails = 0
    for i, n in enumerate(NAMES):
        print(f"[{STATUS[st[i]]}] {i:2d} {n:<24} {vals[i * 6:i * 6 + 6]}")
        fails += st[i] == 2
    print("ALL PASS" if not fails else f"{fails} FAILED", " (value meanings: tests.c detail() / RTT output)")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["soc", "flash", "report", "run"])
    ap.add_argument("hex", nargs="?")
    ap.add_argument("--probe")
    ap.add_argument("--uid")
    a = ap.parse_args()
    probe = make_probe(a)
    if a.cmd == "soc":
        return cmd_soc(probe)
    if a.cmd == "flash":
        return cmd_flash(probe, a.hex)
    if a.cmd == "report":
        return cmd_report(probe)
    return cmd_flash(probe, a.hex) or cmd_report(probe, wait_s=9)


if __name__ == "__main__":
    sys.exit(main())

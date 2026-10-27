#!/usr/bin/env python3
"""
Reads the RAM log of an image built with BSN_LOG_RAM=1 over a J-Link, for
boards without a UART adapter. The target keeps running.

    python ../tools/jlink_log.py build/bsn_c23_hwtest.map
    python ../tools/jlink_log.py build/bsn_c23_hwtest.map --jlink "C:/Program Files/SEGGER/JLink_V962/JLink.exe"
"""
import argparse
import os
import re
import struct
import subprocess
import sys
import tempfile

RAM_SIZE = 8192  # BSN_LOG_RAM_SIZE in common/bsn_log.h


def symbol(mapText, name):
    m = re.search(r"^([0-9a-fA-F]{8})\s+" + name + r"\s*$", mapText, re.M)
    if not m:
        sys.exit(f"{name} not in the map file; was the image built with BSN_LOG_RAM=1?")
    return int(m.group(1), 16)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("map", help="linker map file of the running image")
    ap.add_argument("--jlink", default="C:/Program Files/SEGGER/JLink_V962/JLink.exe")
    ap.add_argument("--device", default="CC2340R5")
    args = ap.parse_args()

    mapText = open(args.map, encoding="utf-8", errors="replace").read()
    bufAddr = symbol(mapText, "bsnLogRam")
    posAddr = symbol(mapText, "bsnLogRamPos")

    with tempfile.TemporaryDirectory() as tmp:
        bufBin = os.path.join(tmp, "buf.bin").replace("\\", "/")
        posBin = os.path.join(tmp, "pos.bin").replace("\\", "/")
        script = os.path.join(tmp, "read.jlink")
        # No halt, no reset: AHB-AP reads while the core runs. Position first,
        # so the buffer read can only contain newer data than the position says.
        with open(script, "w") as f:
            f.write(f"savebin {posBin} 0x{posAddr:08X} 4\n")
            f.write(f"savebin {bufBin} 0x{bufAddr:08X} 0x{RAM_SIZE:X}\n")
            f.write("exit\n")
        r = subprocess.run([args.jlink, "-NoGui", "1", "-ExitOnError", "1", "-Device", args.device,
                            "-If", "SWD", "-Speed", "4000", "-AutoConnect", "1", "-CommandFile", script],
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(bufBin):
            sys.exit("J-Link read failed:\n" + r.stdout[-2000:])
        pos = struct.unpack("<I", open(posBin, "rb").read())[0]
        buf = open(bufBin, "rb").read()

    if pos <= RAM_SIZE:
        data = buf[:pos]
    else:
        start = pos % RAM_SIZE
        data = buf[start:] + buf[:start]
        print(f"[log wrapped: showing the last {RAM_SIZE} of {pos} bytes]")
    sys.stdout.write(data.decode("ascii", errors="replace").replace("\r\n", "\n"))
    print(f"\n[{pos} bytes logged]")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
soak_status.py - live check that every soak node is still heard, read from the scanner CSV.

    python soak_status.py                  # refreshes every 0.5 s, Ctrl+C to stop
    python soak_status.py --once           # print once and exit
    python soak_status.py --window 10      # loss and s/id over the last 10 min instead of 60
    python soak_status.py --csv other.csv --stale 300 --refresh 2 --no-colour

The node list (address, board, place) is read from the placement table in SOAK.md, so a node added there
shows up here. Per node: last contact and its age, RSSI, temperature, RH, VDD, seconds per packet id and the
share of adverts lost over the window (from gaps in the 8-bit packet id, an outage of 256 or more adverts is
not seen). The CSV is only read, never written. Only new lines are read on each refresh.

The loss is advert loss only on the soak build (DRDY=4: one advert per reading, one id per about 5 s). A build
that repeats each reading in several adverts (makefile default, 10 s timer) shows the readings lost instead,
near 0 %. The s/id column shows the build: about 5 s is right, anything else is yellow and its loss is shown
in brackets. After a reflash the old build stays in the window until it has passed.

Colours: status green OK, yellow STALE, red MISSING. Loss over 20 % yellow, over 40 % red. RSSI below -85 dBm
yellow. VDD below 2.7 V yellow, below 2.4 V red (rough flags for a CR2032, not a measured end of life).
"""
import argparse
import collections
import csv
import datetime as dt
import io
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
PREFIX = "FC:DE:C5:73:"
COLOURS = {"green": "32", "yellow": "33", "red": "1;31", "dim": "2", "bold": "1"}
use_colour = True


def c(text: str, colour: str | None) -> str:
    """Wraps already padded text in an ANSI colour, so the column widths stay right."""
    if not use_colour or not colour:
        return text
    return f"\033[{COLOURS[colour]}m{text}\033[0m"


def flag(value: float, warn: float, bad: float, low_is_bad: bool = False) -> str | None:
    if low_is_bad:
        return "red" if value < bad else "yellow" if value < warn else None
    return "red" if value > bad else "yellow" if value > warn else None


def nodes_from_soak_md(path: Path) -> list[tuple[str, str, str]]:
    """(full address, board, place) for each row of the placement table."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(2F:[0-9A-Fa-f]{2})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", line)
        if m:
            out.append((PREFIX + m.group(1).upper(), m.group(2), m.group(3)))
    return out


def ago(seconds: float) -> str:
    s = max(int(seconds), 0)
    if s < 120:
        return f"{s} s"
    if s < 7200:
        return f"{s // 60} min"
    return f"{s // 3600} h {s % 3600 // 60:02d} min"


class CsvTail:
    """Reads the scanner CSV incrementally. Keeps the last row per node and the (time, packet id) pairs
    inside the window."""

    def __init__(self, path: str, window_s: float):
        self.path, self.window = path, dt.timedelta(seconds=window_s)
        self.pos, self.rest, self.rows = 0, b"", 0
        self.last: dict[str, list[str]] = {}
        self.recent: dict[str, collections.deque] = collections.defaultdict(collections.deque)

    def update(self) -> None:
        try:
            size = os.path.getsize(self.path)
        except OSError:
            return
        if size < self.pos:  # file replaced or truncated, start over
            self.__init__(self.path, self.window.total_seconds())
        with open(self.path, "rb") as f:
            f.seek(self.pos)
            data = self.rest + f.read()
            self.pos = f.tell()
        lines = data.split(b"\n")
        self.rest = lines.pop()  # a line still being written stays for the next round
        for r in csv.reader(io.StringIO(b"\n".join(lines).decode("utf-8", errors="replace"))):
            if len(r) < 8:
                continue
            try:
                t, pkt = dt.datetime.fromisoformat(r[0]), int(r[3])
            except ValueError:
                continue
            self.rows += 1
            self.last[r[1]] = r
            self.recent[r[1]].append((t, pkt))

    def window_stats(self, addr: str, now: dt.datetime):
        """(received, lost, s per id) over the window, None for s per id if under two readings."""
        q = self.recent.get(addr)
        if not q:
            return 0, 0, None
        while q and q[0][0] < now - self.window:
            q.popleft()
        rx, lost, advanced = len(q), 0, 0
        for (_, p0), (_, p1) in zip(q, list(q)[1:]):
            lost += (p1 - p0 - 1) % 256
            advanced += (p1 - p0) % 256
        per_id = (q[-1][0] - q[0][0]).total_seconds() / advanced if advanced else None
        return rx, lost, per_id


def render(tail: CsvTail, nodes, args) -> str:
    now = dt.datetime.now()
    out = [f"{now:%Y-%m-%d %H:%M:%S}  {args.csv}  ({tail.rows} rows)"]
    if not tail.last:
        out.append(c("No data in the CSV yet.", "red"))
        return "\n".join(out)
    newest = max(dt.datetime.fromisoformat(r[0]) for r in tail.last.values())
    gap = (now - newest).total_seconds()
    out.append(f"Newest row {ago(gap)} ago"
               + (c("  << SCANNER STOPPED? (no row from any node)", "red") if gap > args.stale else ""))
    out.append("")
    win = f"lost {args.window:g} min"
    out.append(c(f"{'node':6} {'board':5} {'place':40} {'last contact':>19} {'ago':>9} {'RSSI':>5} {'T degC':>6} "
                 f"{'RH %':>6} {'VDD V':>6} {'s/id':>5} {win:>11}  status", "bold"))
    bad = 0
    for addr, board, place in nodes:
        r = tail.last.get(addr)
        if r is None:
            out.append(c(f"{addr[-5:]:6} {board:5} {place[:40]:40} {'never':>19}", "red")
                       + " " * 58 + c("MISSING", "red"))
            bad += 1
            continue
        t = dt.datetime.fromisoformat(r[0])
        age = (now - t).total_seconds()
        rx, lost, per_id = tail.window_stats(addr, now)
        right_build = per_id is not None and abs(per_id - args.period) <= 0.15 * args.period
        loss_pct = 100 * lost / (rx + lost) if rx + lost else None
        loss = "-" if loss_pct is None else f"{loss_pct:.0f} %" if right_build else f"({loss_pct:.0f} %)"
        ok = age <= args.stale
        bad += not ok
        vdd = float(r[6])
        out.append(f"{addr[-5:]:6} {board:5} {place[:40]:40} {t:%Y-%m-%d %H:%M:%S} "
                   + c(f"{ago(age):>9}", None if ok else "yellow") + " "
                   + c(f"{r[2]:>5}", flag(int(r[2]), -85, -200, low_is_bad=True)) + " "
                   + f"{float(r[4]):6.2f} {float(r[5]):6.1f} "
                   + c(f"{vdd:6.3f}", flag(vdd, 2.7, 2.4, low_is_bad=True)) + " "
                   + c(f"{per_id:5.1f}" if per_id else f"{'-':>5}", None if right_build else "yellow") + " "
                   + c(f"{loss:>11}", flag(loss_pct, 20, 40) if loss_pct is not None and right_build else
                       "dim" if loss_pct is not None else None) + "  "
                   + (c("OK", "green") if ok else c("STALE", "yellow")))
    others = sorted(set(tail.last) - {a for a, _, _ in nodes})
    if others:
        out.append(c(f"\nAlso heard, not in SOAK.md: {', '.join(a[-5:] for a in others)}", "dim"))
    out.append("\n" + (c("All nodes OK", "green") if not bad else c(f"{bad} node(s) need a look", "red")))
    return "\n".join(out)


def main() -> None:
    global use_colour
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default=str(HERE / "soak_2026-11-20.csv"))
    ap.add_argument("--soak-md", default=str(HERE / "SOAK.md"))
    ap.add_argument("--stale", type=float, default=120, help="flag a node not heard for this many s (default 120)")
    ap.add_argument("--window", type=float, default=60, help="minutes for loss and s/id (default 60)")
    ap.add_argument("--period", type=float, default=5.0, help="expected s per packet id (default 5, DRDY=4)")
    ap.add_argument("--refresh", type=float, default=0.5, help="seconds between refreshes (default 0.5)")
    ap.add_argument("--once", action="store_true", help="print once and exit")
    ap.add_argument("--no-colour", action="store_true", help="plain text output")
    args = ap.parse_args()

    use_colour = not args.no_colour and sys.stdout.isatty()
    live = not args.once and sys.stdout.isatty()
    if os.name == "nt" and (use_colour or live):
        os.system("")  # turns on ANSI escape handling in the Windows console

    soak_md = Path(args.soak_md)
    tail = CsvTail(args.csv, args.window * 60)
    nodes, md_mtime = None, None
    try:
        while True:
            mtime = soak_md.stat().st_mtime
            if mtime != md_mtime:  # SOAK.md edited, reload the node list
                nodes, md_mtime = nodes_from_soak_md(soak_md), mtime
            tail.update()
            text = render(tail, nodes, args)
            if not live:
                print(text)
                return
            # cursor home, draw, clear what is left of the old screen: no flicker
            sys.stdout.write("\033[H" + text.replace("\n", "\033[K\n") + "\033[K\n\033[J")
            sys.stdout.flush()
            time.sleep(args.refresh)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()

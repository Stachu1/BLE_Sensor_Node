#!/usr/bin/env python3
"""
plot_range.py - RSSI against distance for the LOS walk test of 2026-11-20 (see RANGE.md).

    python plot_range.py                        # dt_01 with the times from RANGE.md
    python plot_range.py --csv other.csv --walk-start 90 --walk-end 240 --distance 163

Distance is not measured per point. The walk is taken as constant speed between --walk-start and --walk-end
(seconds after the first CSV row), from 0 m to --distance. Rows before the walk are plotted at 0 m, rows after
it at --distance, both with hollow markers.
"""
import argparse
import csv
import datetime as dt
from pathlib import Path

import matplotlib.pyplot as plt

HERE = Path(__file__).parent
BOARDS = {  # address -> (label, colour)
    "FC:DE:C5:73:2F:7B": ("Rev A (A #3, chip antenna)", "#2e9e44"),
    "FC:DE:C5:73:2F:5A": ("Rev B (B #2, trace IFA)", "#1f6fd1"),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default=str(HERE / "dt_01_C23-AvB_5s_0s2_0dBm.csv"))
    ap.add_argument("--walk-start", type=float, default=90, help="s after the first row (default 90)")
    ap.add_argument("--walk-end", type=float, default=240, help="s after the first row (default 240)")
    ap.add_argument("--distance", type=float, default=163, help="end distance in m (default 163)")
    ap.add_argument("--mark", type=float, default=30, help="reference distance line in m (default 30)")
    args = ap.parse_args()

    rows = list(csv.reader(open(args.csv, newline="")))
    t0 = dt.datetime.fromisoformat(rows[0][0])
    speed = args.distance / (args.walk_end - args.walk_start)

    data = {a: {"t": [], "d": [], "rssi": [], "phase": []} for a in BOARDS}
    for r in rows:
        addr = r[1]
        if addr not in data:
            continue
        t = (dt.datetime.fromisoformat(r[0]) - t0).total_seconds()
        if t < args.walk_start:
            d, phase = 0.0, "before"
        elif t > args.walk_end:
            d, phase = args.distance, "after"
        else:
            d, phase = (t - args.walk_start) * speed, "walk"
        for k, v in zip(("t", "d", "rssi", "phase"), (t, d, int(r[2]), phase)):
            data[addr][k].append(v)

    fig, (ax_d, ax_t) = plt.subplots(2, 1, figsize=(8, 7.5), gridspec_kw={"height_ratios": [3, 2]})
    for addr, (label, colour) in BOARDS.items():
        s = data[addr]
        walk = [i for i, p in enumerate(s["phase"]) if p == "walk"]
        still = [i for i, p in enumerate(s["phase"]) if p != "walk"]
        ax_d.plot([s["d"][i] for i in walk], [s["rssi"][i] for i in walk], "-o", color=colour, lw=2, ms=6,
                  label=f"{label}, walking")
        ax_d.plot([s["d"][i] for i in still], [s["rssi"][i] for i in still], "o", mfc="none", mec=colour,
                  mew=1.5, ms=7, label=f"{label}, standing")
        ax_t.plot(s["t"], s["rssi"], "-o", color=colour, lw=2, ms=4, label=label)
        print(f"{label}: {len(s['t'])} rows, RSSI {min(s['rssi'])} to {max(s['rssi'])} dBm, "
              f"at {args.distance:.0f} m: {min(s['rssi'][i] for i in still if s['phase'][i] == 'after')} to "
              f"{max(s['rssi'][i] for i in still if s['phase'][i] == 'after')} dBm")

    ax_d.axvline(args.mark, color="0.4", ls="--", lw=1)
    ax_d.text(args.mark + 2, -38, f"{args.mark:.0f} m", color="0.3", va="top")
    ax_d.set_xlabel("Distance from the nodes (m), constant walking speed assumed")
    ax_d.set_ylabel("RSSI at the NINA-W15 (dBm)")
    ax_d.set_xlim(-5, args.distance + 5)
    ax_d.set_title("LOS walk test, 0 dBm, both nodes about 2 m above ground, 2026-11-20")
    ax_d.legend(fontsize=8, loc="upper right")

    ax_t.axvspan(args.walk_start, args.walk_end, color="0.9", zorder=0)
    ax_t.text((args.walk_start + args.walk_end) / 2, -38, "walking", ha="center", va="top", color="0.3")
    ax_t.set_xlabel(f"Time after the first logged row, {t0:%H:%M:%S} (s)")
    ax_t.set_ylabel("RSSI (dBm)")
    ax_t.legend(fontsize=8, loc="upper right")

    for ax in (ax_d, ax_t):
        ax.set_ylim(-100, -35)
        ax.grid(True, color="0.88", lw=0.8)
        ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    out = Path(args.csv).with_suffix(".png")
    fig.savefig(out, dpi=200)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()

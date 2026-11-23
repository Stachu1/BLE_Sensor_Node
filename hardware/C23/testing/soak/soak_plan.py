#!/usr/bin/env python3
"""
soak_plan.py - temperature and RH from the soak nodes drawn on the floor plan of the flat, as an MP4 and a still.

    python soak_plan.py                                   # whole CSV, 1 frame per min, MP4 + last-frame still
    python soak_plan.py --step 120 --fps 15               # 1 frame per 2 min of data
    python soak_plan.py --start 2026-11-20T22:00 --end 2026-11-21T08:00
    python soak_plan.py --still 2026-11-20T23:00          # still at this time (default: last frame)
    python soak_plan.py --no-video                        # still only

The plan (rooms, doors, windows, node positions, data cuts) is read from flat_plan.yaml, --plan points elsewhere.
skip_first_min in the plan drops the first minutes after the first CSV row (nodes settling after placement),
--start overrides it.

Between the nodes the field is an interpolation, not a measurement. It is an inverse-distance weighting
(power 2) where the distance is the walking distance on a 5 cm grid, through door openings only, not the straight
line. Walls therefore block the blending, a room mostly follows its own node(s) and the doorways mix between
rooms. Places no active node can reach stay blank, places outside the rooms (the notch next to the entrance) are
hatched. The node markers carry the measured value.

Each node's value in a frame is the mean of its readings in the last --window seconds (default 180). A node with
no reading in that window is left out of the frame and drawn hollow. Colour scales are fixed over the whole run.
"""
import argparse
import csv
import datetime as dt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml
from matplotlib import animation
from matplotlib.path import Path as MPath
from matplotlib.patches import Polygon
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

HERE = Path(__file__).parent
PREFIX = "FC:DE:C5:73:"
RES = 5.0          # grid cell, cm
D0 = 40.0          # added to every distance so a node does not make a sharp spike, cm
POWER = 2.0

INK = "#1f2328"
MUTED = "#6e7781"
WALL = "#24292f"
WINDOW = "#7aa7d6"


def load_csv(path: Path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.reader(f):
            if len(r) != 8:
                continue
            try:
                t = dt.datetime.fromisoformat(r[0])
                rows.append((t, r[1].removeprefix(PREFIX), float(r[4]), float(r[5])))
            except ValueError:
                continue    # last line may be half written by the scanner
    return rows


def wall_segments(plan):
    """Room edges with the door openings cut out (edges are axis aligned)."""
    segs = []
    for poly in plan["rooms"].values():
        pts = [tuple(map(float, p)) for p in poly]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
            pieces = [((x1, y1), (x2, y2))]
            for d in plan["doors"]:
                (ax, ay), (bx, by) = d["a"], d["b"]
                out = []
                for (px, py), (qx, qy) in pieces:
                    if px == qx == ax == bx:      # vertical, same line
                        lo, hi = sorted((py, qy)); dlo, dhi = sorted((ay, by))
                        if dhi <= lo or dlo >= hi:
                            out.append(((px, py), (qx, qy))); continue
                        if dlo > lo: out.append(((px, lo), (px, dlo)))
                        if dhi < hi: out.append(((px, dhi), (px, hi)))
                    elif py == qy == ay == by:    # horizontal, same line
                        lo, hi = sorted((px, qx)); dlo, dhi = sorted((ax, bx))
                        if dhi <= lo or dlo >= hi:
                            out.append(((px, py), (qx, qy))); continue
                        if dlo > lo: out.append(((lo, py), (dlo, py)))
                        if dhi < hi: out.append(((dhi, py), (hi, py)))
                    else:
                        out.append(((px, py), (qx, qy)))
                pieces = out
            segs += pieces
    return segs


class Grid:
    def __init__(self, plan):
        allpts = np.array([p for poly in plan["rooms"].values() for p in poly], float)
        self.w, self.h = allpts.max(axis=0)
        self.nx, self.ny = int(round(self.w / RES)), int(round(self.h / RES))
        xc = (np.arange(self.nx) + 0.5) * RES
        yc = (np.arange(self.ny) + 0.5) * RES
        X, Y = np.meshgrid(xc, yc)
        pts = np.column_stack([X.ravel(), Y.ravel()])
        self.label = np.full(pts.shape[0], -1)
        for k, poly in enumerate(plan["rooms"].values()):
            self.label[MPath(np.array(poly, float)).contains_points(pts)] = k
        self.label = self.label.reshape(self.ny, self.nx)
        self.graph = self._graph(plan["doors"])

    def _on_door(self, x, y, doors, vertical):
        ok = np.zeros(x.shape, bool)
        for d in doors:
            (ax, ay), (bx, by) = d["a"], d["b"]
            if vertical and ax == bx:
                ok |= (np.abs(x - ax) < 1e-6) & (y >= min(ay, by)) & (y <= max(ay, by))
            if not vertical and ay == by:
                ok |= (np.abs(y - ay) < 1e-6) & (x >= min(ax, bx)) & (x <= max(ax, bx))
        return ok

    def _graph(self, doors):
        L = self.label
        idx = np.arange(L.size).reshape(L.shape)
        rows, cols, wts = [], [], []
        # right neighbour, boundary is a vertical line
        a, b = L[:, :-1], L[:, 1:]
        ii, jj = np.meshgrid(np.arange(self.ny), np.arange(self.nx - 1), indexing="ij")
        bx, by = (jj + 1) * RES, (ii + 0.5) * RES
        ok = (a >= 0) & (b >= 0) & ((a == b) | self._on_door(bx, by, doors, True))
        rows.append(idx[:, :-1][ok]); cols.append(idx[:, 1:][ok]); wts.append(np.full(ok.sum(), RES))
        # upper neighbour, boundary is a horizontal line
        a, b = L[:-1, :], L[1:, :]
        ii, jj = np.meshgrid(np.arange(self.ny - 1), np.arange(self.nx), indexing="ij")
        bx, by = (jj + 0.5) * RES, (ii + 1) * RES
        ok = (a >= 0) & (b >= 0) & ((a == b) | self._on_door(bx, by, doors, False))
        rows.append(idx[:-1, :][ok]); cols.append(idx[1:, :][ok]); wts.append(np.full(ok.sum(), RES))
        # diagonals, only inside one room
        c00, c01, c10, c11 = L[:-1, :-1], L[:-1, 1:], L[1:, :-1], L[1:, 1:]
        ok = (c00 >= 0) & (c00 == c01) & (c00 == c10) & (c00 == c11)
        for s, t in ((idx[:-1, :-1], idx[1:, 1:]), (idx[:-1, 1:], idx[1:, :-1])):
            rows.append(s[ok]); cols.append(t[ok]); wts.append(np.full(ok.sum(), RES * np.sqrt(2)))
        r, c, w = map(np.concatenate, (rows, cols, wts))
        return coo_matrix((w, (r, c)), shape=(L.size, L.size)).tocsr()

    def distances(self, xys):
        cells = [int(y // RES) * self.nx + int(x // RES) for x, y in xys]
        for (x, y), cell in zip(xys, cells):
            if self.label.ravel()[cell] < 0:
                raise SystemExit(f"node at {x}, {y} is outside every room")
        d = dijkstra(self.graph, directed=False, indices=cells)
        return d.reshape(len(cells), self.ny, self.nx)


def frame_values(rows, nodes, cuts, times, window):
    """vals[k, i, n]: mean of quantity k (0 T, 1 RH) for node n in (t_i - window, t_i], NaN if none."""
    vals = np.full((2, len(times), len(nodes)), np.nan)
    tsec = np.array([t.timestamp() for t in times])
    for n, addr in enumerate(nodes):
        cut = cuts.get(addr)
        r = [x for x in rows if x[1] == addr and (cut is None or x[0] >= cut)]
        if not r:
            continue
        ts = np.array([x[0].timestamp() for x in r])
        order = np.argsort(ts); ts = ts[order]
        q = np.array([[x[2], x[3]] for x in r])[order]
        cs = np.vstack([np.zeros(2), np.cumsum(q, axis=0)])
        hi = np.searchsorted(ts, tsec, side="right")
        lo = np.searchsorted(ts, tsec - window, side="right")
        cnt = hi - lo
        m = cnt > 0
        vals[:, m, n] = ((cs[hi[m]] - cs[lo[m]]) / cnt[m, None]).T
    return vals


def idw(dist, v):
    m = ~np.isnan(v) & np.isfinite(dist).any(axis=(1, 2))
    if not m.any():
        return np.full(dist.shape[1:], np.nan)
    d, v = dist[m], v[m]
    w = np.where(np.isfinite(d), 1.0 / (d + D0) ** POWER, 0.0)
    s = w.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(s > 0, (w * v[:, None, None]).sum(axis=0) / s, np.nan)


def nice_range(a, step):
    a = a[np.isfinite(a)]
    lo, hi = np.percentile(a, [1, 99])
    return np.floor(lo / step) * step, np.ceil(hi / step) * step


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, default=HERE / "soak_2026-11-20.csv")
    ap.add_argument("--plan", type=Path, default=HERE / "flat_plan.yaml")
    ap.add_argument("--step", type=float, default=60, help="data seconds per frame")
    ap.add_argument("--window", type=float, default=180, help="averaging window per node, s")
    ap.add_argument("--fps", type=int, default=12)
    ap.add_argument("--start"); ap.add_argument("--end")
    ap.add_argument("--still", help="time of the still, default last frame")
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--out", type=Path, help="output prefix, default soak_plan_<csv date> next to the CSV")
    a = ap.parse_args()

    plan = yaml.safe_load(a.plan.read_text())
    nodes = list(plan["nodes"])
    cuts = {k: dt.datetime.fromisoformat(v) for k, v in (plan.get("cut_before") or {}).items()}
    rows = load_csv(a.csv)
    skip = dt.timedelta(minutes=float(plan.get("skip_first_min") or 0))
    t0 = dt.datetime.fromisoformat(a.start) if a.start else min(r[0] for r in rows) + skip
    t1 = dt.datetime.fromisoformat(a.end) if a.end else max(r[0] for r in rows)
    t0 = t0.replace(second=0, microsecond=0) + dt.timedelta(minutes=1)
    n = int((t1 - t0).total_seconds() // a.step) + 1
    times = [t0 + dt.timedelta(seconds=a.step * i) for i in range(n)]
    out = a.out or a.csv.with_name(a.csv.stem.replace("soak_", "soak_plan_"))

    grid = Grid(plan)
    xys = [plan["nodes"][k]["xy"] for k in nodes]
    dist = grid.distances(xys)
    vals = frame_values(rows, nodes, cuts, times, a.window)
    qty = [("Temperature", "°C", "RdBu_r", 0.5, "{:.1f}"), ("Relative humidity", "%", "Blues", 5, "{:.0f}")]
    ranges = [nice_range(vals[k], q[3]) for k, q in enumerate(qty)]
    outside = grid.label < 0
    # hatch only the gaps inside the flat (not part of any room), not the space around it
    from scipy import ndimage
    comp, _ = ndimage.label(outside)
    edge = set(np.unique(np.concatenate([comp[0], comp[-1], comp[:, 0], comp[:, -1]])))
    gaps = outside & ~np.isin(comp, list(edge))

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), facecolor="white")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.88, bottom=0.12, wspace=0.06)
    ims, markers, texts = [], [], []
    ext = (0, grid.w, 0, grid.h)
    for k, (ax, (name, unit, cmap, _, fmt)) in enumerate(zip(axes, qty)):
        ax.set_aspect("equal"); ax.axis("off")
        ax.set_xlim(-20, grid.w + 20); ax.set_ylim(-20, grid.h + 20)
        im = ax.imshow(np.full(outside.shape, np.nan), origin="lower", extent=ext, cmap=cmap,
                       vmin=ranges[k][0], vmax=ranges[k][1], interpolation="bilinear", zorder=1)
        ims.append(im)
        ax.contourf(np.linspace(0, grid.w, grid.nx), np.linspace(0, grid.h, grid.ny), gaps.astype(float),
                    levels=[0.5, 1.5], colors="none", hatches=["////"], zorder=2)
        for s in wall_segments(plan):
            ax.plot(*zip(*s), color=WALL, lw=2.2, solid_capstyle="projecting", zorder=4)
        for wdw in plan["windows"]:
            ax.plot(*zip(wdw["a"], wdw["b"]), color=WINDOW, lw=5, solid_capstyle="butt", zorder=5)
        for rname, poly in plan["rooms"].items():
            p = np.array(poly, float)
            ax.text(p[:, 0].mean(), p[:, 1].mean(), rname, ha="center", va="center", fontsize=9,
                    color=MUTED, zorder=3)
        mk = ax.scatter([p[0] for p in xys], [p[1] for p in xys], s=70, c=[INK] * len(xys),
                        edgecolors="white", linewidths=2, zorder=6)
        markers.append(mk)
        texts.append([ax.text(x, y + 22, "", ha="center", va="bottom", fontsize=8.5, color=INK, zorder=7,
                              bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
                      for x, y in xys])
        cax = fig.add_axes([ax.get_position().x0 + 0.1, 0.07, ax.get_position().width - 0.2, 0.025])
        cb = fig.colorbar(im, cax=cax, orientation="horizontal")
        cb.set_label(f"{name} ({unit})", color=INK, fontsize=9); cb.outline.set_visible(False)
        cax.tick_params(labelsize=8, colors=MUTED)
    title = fig.suptitle("", fontsize=12, color=INK, y=0.97)
    fig.text(0.5, 0.905, "Dots are measured (hollow: no reading in the last 3 min). Colour between them is "
             "interpolated through the doors, not measured.", ha="center", fontsize=8.5, color=MUTED)

    def draw(i):
        for k, (_, _, _, _, fmt) in enumerate(qty):
            v = vals[k, i]
            ims[k].set_data(np.ma.masked_invalid(np.where(outside, np.nan, idw(dist, v))))
            markers[k].set_facecolors([INK if np.isfinite(x) else "white" for x in v])
            markers[k].set_edgecolors(["white" if np.isfinite(x) else INK for x in v])
            for txt, x in zip(texts[k], v):
                txt.set_text(fmt.format(x) if np.isfinite(x) else "")
                txt.set_visible(bool(np.isfinite(x)))
        title.set_text(f"Soak, flat, {times[i]:%a %d %b %Y  %H:%M}")
        return ims + markers + [title]

    if not a.no_video:
        import imageio_ffmpeg
        plt.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()
        w = animation.FFMpegWriter(fps=a.fps, codec="libx264", bitrate=-1,
                                   extra_args=["-pix_fmt", "yuv420p", "-crf", "20"])
        with w.saving(fig, str(out) + ".mp4", dpi=120):
            for i in range(len(times)):
                draw(i); w.grab_frame()
        print(f"{out}.mp4: {len(times)} frames, {times[0]:%H:%M} to {times[-1]:%H:%M}")

    si = len(times) - 1
    if a.still:
        ts = dt.datetime.fromisoformat(a.still)
        si = int(np.argmin([abs((t - ts).total_seconds()) for t in times]))
    draw(si)
    fig.savefig(str(out) + "_still.png", dpi=200)
    print(f"{out}_still.png at {times[si]:%Y-%m-%d %H:%M}")


if __name__ == "__main__":
    main()

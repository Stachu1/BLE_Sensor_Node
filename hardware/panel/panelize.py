"""
Panelize BSN-C23 and BSN-N54 into a 2x2 panel for JLCPCB.

Layout (top view):

    |rail| C23 | C23 |rail|
    |rail| N54 | N54 |rail|     (N54 rotated 180 deg)

Both boards are 34x34 mm rounded squares (corner radius 15.5 mm), leaving a
3 mm flat in the middle of each side. Every flat that faces a neighbour or a
rail gets a 3 mm wide mouse-bite tab. Rails are 5 mm on the left and right
only; no fiducials or tooling holes (hand assembly).

N54 is rotated 180 deg so that the antennas of both boards face the outer
(tab-free) top/bottom edges of the panel; otherwise the C23<->N54 tab lands on
N54's antenna pads.

Run with KiCad's bundled Python (KiKit installed there):
    "C:/Program Files/KiCad/10.0/bin/python.exe" panelize.py
"""

from pathlib import Path

import kikit.substrate
from kikit.panelize import Panel, Origin
from kikit.units import mm
from kikit.common import fromMm, fromDegrees
from pcbnew import VECTOR2I
from shapely.geometry import Polygon

HERE = Path(__file__).resolve().parent
C23 = HERE.parent / "C23" / "BSN-C23.kicad_pcb"
N54 = HERE.parent / "N54" / "BSN-N54.kicad_pcb"
OUT = HERE / "BSN-panel.kicad_pcb"

BOARD = 34 * mm          # board size
SPACING = 2 * mm         # gap between boards / board-to-rail (JLC: >= 1.6 mm)
RAIL = 5 * mm            # JLC recommended rail width
TAB_WIDTH = 3 * mm       # width of the flat section of the outline

# Mouse bites: 4 x 0.5 mm holes per tab, centred on the board edge. KiKit
# spreads int(length / spacing) + 1 holes evenly over the (unprolonged) 3 mm
# cut, so 0.99 mm gives 4 holes at 1 mm pitch, the outer two on the tab sides.
MB_DIAMETER = 0.5 * mm
MB_SPACING = 0.99 * mm
MB_OFFSET = 0
MB_PROLONG = 0

PANEL_W, PANEL_H = 84 * mm, 70 * mm   # 2 * (RAIL + SPACING) + 2 * BOARD + SPACING

# No addMillFillets(): its buffer-out/in pass jitters every outline vertex by
# a few um, so the rails no longer sit on the grid. JLC's router rounds the
# inner corners by itself anyway.

# Panel centre (arbitrary, just keeps it on the A4 sheet)
CX, CY = 150 * mm, 100 * mm
PITCH = BOARD + SPACING


def _rectToShapely(rect):
    # KiKit rounds rect corners with shapely's default 16 segments per
    # quarter circle, which is too coarse: the facets cut into the edge
    # clearance and prevent arc reconstruction on save. Use a fine one.
    poly = Polygon([tuple(c) for c in rect.GetRectCorners()])
    radius = rect.GetCornerRadius()
    if radius == 0:
        return poly
    return (poly.buffer(-radius, join_style="round", quad_segs=256)
                .buffer(radius, join_style="round", quad_segs=256))


kikit.substrate.rectToShapely = _rectToShapely


def main():
    panel = Panel(str(OUT))
    panel.inheritDesignSettings(str(C23))
    panel.inheritProperties(str(C23))

    # Board centres: columns at -/+ PITCH/2, row 0 = C23 (top), row 1 = N54
    cols = [CX - PITCH // 2, CX + PITCH // 2]
    rows = [(CY - PITCH // 2, C23, 0), (CY + PITCH // 2, N54, 180)]
    for y, board, angle in rows:
        for x in cols:
            # Nets get a per-board prefix (default); refdes are kept as-is
            panel.appendBoard(
                str(board), VECTOR2I(int(x), int(y)), origin=Origin.Center,
                rotationAngle=fromDegrees(angle),
                tolerance=fromMm(1),
                inheritDrc=(board == C23))  # KiKit can only take one rule set

    panel.makeRailsLr(RAIL, hspace=SPACING)

    cuts = []

    def bridge(origin, dirA, dirB, cutA=True, cutB=True):
        # Tab spanning a gap: grow from the gap centre towards both sides.
        # Build both halves before appending, otherwise the second half would
        # start inside the first one. The ray is capped at the gap width:
        # KiKit takes the first substrate hit in iteration order, not the
        # nearest, so a long ray can tunnel through a board to the rail.
        halves = [panel.boardSubstrate.tab(origin, d, TAB_WIDTH,
                                           maxHeight=SPACING)
                  for d in (dirA, dirB)]
        for (t, cut), keep in zip(halves, (cutA, cutB)):
            panel.appendSubstrate(t)
            if keep:
                cuts.append(cut)

    left, right = (-1, 0), (1, 0)
    up, down = (0, -1), (0, 1)

    for y, _, _ in rows:
        # board <-> board (horizontal neighbours)
        bridge((CX, y), left, right)
        # left rail <-> board, right board <-> right rail (no cut on the rail)
        bridge((cols[0] - PITCH // 2, y), left, right, cutA=False)
        bridge((cols[1] + PITCH // 2, y), left, right, cutB=False)

    for x in cols:
        # C23 <-> N54 (vertical neighbours)
        bridge((x, CY), up, down)

    minx, miny, maxx, maxy = panel.boardSubstrate.bounds()
    assert (maxx - minx, maxy - miny) == (PANEL_W, PANEL_H), \
        f"panel is {(maxx - minx) / mm} x {(maxy - miny) / mm} mm"

    panel.makeMouseBites(cuts, MB_DIAMETER, MB_SPACING, MB_OFFSET, MB_PROLONG)
    panel.save(reconstructArcs=True, refillAllZones=True)

    print(f"Saved {OUT}")
    print(f"Panel size: {(maxx - minx) / mm:.2f} x {(maxy - miny) / mm:.2f} mm")


if __name__ == "__main__":
    main()

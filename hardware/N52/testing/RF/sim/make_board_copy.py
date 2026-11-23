"""Make a simulation copy of BSN-N52.kicad_pcb with a MIFA footprint at a chosen site and GND pours (KiCad python).

The user's board is only read. The copy goes to boards/<name>/<name>.kicad_pcb and is meant for export_board.py
(./sim.sh export does not use it, run export_board.py on the copy). Open the copy in KiCad to look at it.

Usage:
    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" make_board_copy.py <name> --fp <dir.pretty> <footprint>
        [--x 146.0 --y 93.0 --rot 0] [--board ../../../BSN-N52.kicad_pcb] [--no-pour] [--vias 2.0]

What it does to the copy:
    - removes AE1 and places the given footprint as AE1 at (x, y, rot) in KiCad mm, pad 1 on the antenna feed net
      (the net of the old AE1 pad 1), pad 2 on GND
    - GND zones on every copper layer over the whole outline (0.25 mm clearance, solid pad connection), the AE1
      keep-out clears them
    - GND vias: a fence 0.6 mm below the antenna ground edge (1.5 mm pitch) and a grid (--vias mm pitch) over the
      rest, wherever they keep 0.35 mm from every pad and track (a crude placement for the sims, not for production)
    - the feed trace is NOT routed: the sims put their port across the feed notch, the reference plane is the notch
      bottom. Put the matching network right at the notch bottom on the real board.
    - zones filled, saved
"""
import argparse
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
mm = pcbnew.FromMM
tomm = pcbnew.ToMM


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('name')
	ap.add_argument('--fp', nargs=2, required=True, metavar=('LIBDIR', 'FOOTPRINT'))
	ap.add_argument('--x', type=float, default=146.0)
	ap.add_argument('--y', type=float, default=93.0)
	ap.add_argument('--rot', type=float, default=0.0)
	ap.add_argument('--board', default=os.path.join(HERE, '..', '..', '..', 'BSN-N52.kicad_pcb'))
	ap.add_argument('--no-pour', action='store_true')
	ap.add_argument('--vias', type=float, default=2.0)
	a = ap.parse_args()

	out_dir = os.path.join(HERE, 'boards', a.name)
	out = os.path.join(out_dir, a.name + '.kicad_pcb')
	if os.path.exists(out):
		sys.exit(out + ' exists, use a new name')
	os.makedirs(out_dir, exist_ok=True)
	b = pcbnew.LoadBoard(os.path.abspath(a.board))
	gnd = b.FindNet('GND')
	old = b.FindFootprintByReference('AE1')
	feed_net = None
	if old is not None:
		for p in old.Pads():
			if p.GetNumber() == '1':
				feed_net = p.GetNet()
		b.Remove(old)
	fp = pcbnew.FootprintLoad(os.path.abspath(a.fp[0]), a.fp[1])
	if fp is None:
		sys.exit('footprint not found')
	fp.SetReference('AE1')
	fp.SetPosition(pcbnew.VECTOR2I(mm(a.x), mm(a.y)))
	fp.SetOrientationDegrees(a.rot)
	b.Add(fp)
	for p in fp.Pads():
		if p.GetNumber() == '1' and feed_net is not None:
			p.SetNet(feed_net)
		if p.GetNumber() == '2':
			p.SetNet(gnd)

	ol = pcbnew.SHAPE_POLY_SET()
	b.GetBoardPolygonOutlines(ol, False)
	bb = ol.BBox()
	layers = [l for l in b.GetEnabledLayers().CuStack()]
	if not a.no_pour:
		for lid in layers:
			z = pcbnew.ZONE(b)
			z.SetLayer(lid)
			z.SetNet(gnd)
			z.SetLocalClearance(mm(0.25))
			z.SetMinThickness(mm(0.2))
			z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
			z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
			z.Outline().NewOutline()
			for x, y in ((bb.GetLeft(), bb.GetTop()), (bb.GetRight(), bb.GetTop()), (bb.GetRight(), bb.GetBottom()), (bb.GetLeft(), bb.GetBottom())):
				z.Outline().Append(x, y)
			b.Add(z)

	# keep-out region of the new AE1 (no vias in it)
	ko = [z.GetBoundingBox() for z in fp.Zones()]

	def in_ko(x, y, m=0.5):
		return any(tomm(k.GetLeft()) - m < x < tomm(k.GetRight()) + m and tomm(k.GetTop()) - m < y < tomm(k.GetBottom()) + m for k in ko)

	obst = []
	for f in b.GetFootprints():
		for p in f.Pads():
			r = p.GetBoundingBox()
			obst.append((tomm(r.GetLeft()), tomm(r.GetTop()), tomm(r.GetRight()), tomm(r.GetBottom())))
	for t in b.GetTracks():
		r = t.GetBoundingBox()
		obst.append((tomm(r.GetLeft()), tomm(r.GetTop()), tomm(r.GetRight()), tomm(r.GetBottom())))
	x0, x1, y0, y1 = tomm(bb.GetLeft()), tomm(bb.GetRight()), tomm(bb.GetTop()), tomm(bb.GetBottom())

	def free(x, y, r=0.3 + 0.35):
		if not (x0 + 0.8 < x < x1 - 0.8 and y0 + 0.8 < y < y1 - 0.8) or in_ko(x, y, 0.4):
			return False
		return all(not (bx0 - r < x < bx1 + r and by0 - r < y < by1 + r) for bx0, by0, bx1, by1 in obst)

	pts = []
	gy = max(tomm(k.GetBottom()) for k in ko[:1]) + 0.6 if ko else None
	if gy is not None:
		x = x0 + 1.0
		while x < x1 - 0.8:
			pts.append((x, gy))
			x += 1.5
	y = y0 + 1.0
	while y < y1 - 0.8:
		x = x0 + 1.0
		while x < x1 - 0.8:
			pts.append((x, y))
			x += a.vias
		y += a.vias
	n = 0
	for x, y in pts:
		if not free(x, y):
			continue
		v = pcbnew.PCB_VIA(b)
		v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
		v.SetWidth(mm(0.6))
		v.SetDrill(mm(0.3))
		v.SetNet(gnd)
		b.Add(v)
		obst.append((x - 0.3, y - 0.3, x + 0.3, y + 0.3))
		n += 1
	pcbnew.ZONE_FILLER(b).Fill(b.Zones())
	pcbnew.SaveBoard(out, b)
	print('wrote %s: AE1 = %s at (%.2f, %.2f) rot %.0f, %s, %d GND vias' % (out, a.fp[1], a.x, a.y, a.rot,
		'no pour' if a.no_pour else 'GND pours on %d layers' % len(layers), n))


if __name__ == '__main__':
	main()

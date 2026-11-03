"""Make a bigger copy of an exported board (board.json) to see what a larger ground plane would buy.

Everything beyond a cut line moves outward by d mm: outline, copper on all layers, vias, pads, the AE1 copper.
Polygons that cross the cut line are stretched, so the ground (and any trace crossing the line) gets longer.
The antenna area and the RF parts must stay on the fixed side of the cut.

    python stretch_board.py build/b2/board.json build/b2t10 --dy 10          # taller: y < -10 moves down
    python stretch_board.py build/b2/board.json build/b2w6 --dx 6            # wider: x > 6.9 moves right

Cut lines (sim coordinates): y = -10 lies between U1 / BT1 pads and the bottom edge, x = 6.9 lies just left of the
right R10 corner centre (x = 7), so the corner arc moves as a whole. Add a matching entry to antenna.BASES
(the right corner centre moves with --dx).
"""
import argparse
import json
import os

YCUT = -10.0
XCUT = 6.9


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('src')
	ap.add_argument('out_dir')
	ap.add_argument('--dy', type=float, default=0.0)
	ap.add_argument('--dx', type=float, default=0.0)
	a = ap.parse_args()

	def mv(x, y):
		if a.dx and x > XCUT:
			x += a.dx
		if a.dy and y < YCUT:
			y -= a.dy
		return x, y

	def mvpoly(pts):
		return [list(mv(x, y)) for x, y in pts]

	b = json.load(open(a.src))
	b['outline'] = [mvpoly(o) for o in b['outline']]
	b['copper'] = {k: [mvpoly(p) for p in v] for k, v in b['copper'].items()}
	b['ae1']['copper'] = [mvpoly(p) for p in b['ae1']['copper']]
	# fill the stretched gap with copies of the vias next to the cut (keeps the edge via fence and the stitching)
	extra = []
	for v in b['vias']:
		if a.dx and XCUT - a.dx < v['x'] <= XCUT:
			extra.append(dict(v, x=v['x'] + a.dx))
		if a.dy and YCUT <= v['y'] < YCUT + a.dy:
			extra.append(dict(v, y=v['y'] - a.dy))
	for v in b['vias']:
		v['x'], v['y'] = mv(v['x'], v['y'])
	b['vias'] += extra
	for ref, fp in b['pads'].items():
		fp['pos'] = list(mv(*fp['pos']))
		for p in fp['pads']:
			p['c'] = list(mv(*p['c']))
			x0, y0 = mv(p['bbox'][0], p['bbox'][1])
			x1, y1 = mv(p['bbox'][2], p['bbox'][3])
			p['bbox'] = [x0, y0, x1, y1]
	b['source'] = '%s stretched dx %g dy %g (stretch_board.py)' % (b.get('source', a.src), a.dx, a.dy)
	os.makedirs(a.out_dir, exist_ok=True)
	json.dump(b, open(os.path.join(a.out_dir, 'board.json'), 'w'))
	print('wrote', os.path.join(a.out_dir, 'board.json'))


if __name__ == '__main__':
	main()

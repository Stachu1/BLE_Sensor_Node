"""Synthetic test boards (board.json, same format as export_board.py) for antenna sims before the real board exists.

Usage (laptop or server, numpy only):
    python synth_board.py build/<name> [options]
    --shape disc|rect     outline (default disc)
    --d 30                disc diameter (mm)
    --w 30 --h 30 --r 3   rect width, height, corner radius
    --clear 6             ground edge distance below the top board edge at x = 0 (antenna clearance)
    --layers 2|4          copper layers (all ground below the ground edge), default 2
    --t 1.0               board thickness, --er 4.5, --tand 0.02
    --battery B|F|none    CR1632 in the Assmann A-BAT-CH-C6-EA-CSR1 holder on the bottom / top side (default B)
    --bat 0,-2            cell centre (mm, sim coordinates), --bat-rot 0|90 holder rotation
    --site -3             feed point x on the ground edge (the antenna site), --mirror for an arm towards -x
    --notch W,D           cut a feed notch into the ground polygons at the site (validation of the copper cut)

Simulation coordinates as everywhere: origin at the board centre, y up, F.Cu at the top (+z), B.Cu at z = 0.
The KiCad coordinates of the drawings are x + 150, 100 - y (origin_kicad).
The ground pours of all layers are joined by a via fence 0.6 mm below the ground edge (1.5 mm pitch) and a 3 mm
via grid. The battery holder's + pads are part of the ground (VDD is decoupled to ground at RF, an assumption).
"""
import argparse
import json
import math
import os

import numpy as np

CR1632 = {'d': 16.0, 't': 3.2, 'gap': 0.2}
# Assmann A-BAT-CH-C6-EA-CSR1 (library/BSN-N52.pretty): + clip pads "1" at x +-10.2 (3.6 x 4), - pad "2" 5 x 5 at the centre
HOLDER_PADS = [('1', (-10.2, 0.0), (3.6, 4.0)), ('1', (10.2, 0.0), (3.6, 4.0)), ('2', (0.0, 0.0), (5.0, 5.0))]


def outline_disc(d, n=144):
	a = np.linspace(0, 2 * np.pi, n, endpoint=False)
	return [[round(d / 2 * math.cos(t), 4), round(d / 2 * math.sin(t), 4)] for t in a]


def outline_rect(w, h, r, n=12):
	if r <= 0:
		return [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]]
	pts = []
	for cx, cy, a0 in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)):
		for t in np.linspace(a0, a0 + 90, n):
			pts.append([round(cx + r * math.cos(math.radians(t)), 4), round(cy + r * math.sin(math.radians(t)), 4)])
	return pts


def clip_below(poly, ye):
	"""Sutherland-Hodgman clip of a polygon to y <= ye."""
	out = []
	for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
		in0, in1 = y0 <= ye, y1 <= ye
		if in0:
			out.append([x0, y0])
		if in0 != in1:
			t = (ye - y0) / (y1 - y0)
			out.append([round(x0 + t * (x1 - x0), 4), ye])
	return out


def insert_notch(poly, ye, xc, w, d):
	"""Cut a rectangular notch (width w, depth d, centred at xc) into the straight edge y = ye of a polygon."""
	for i in range(len(poly)):
		a, b = poly[i], poly[(i + 1) % len(poly)]
		if abs(a[1] - ye) < 1e-9 and abs(b[1] - ye) < 1e-9 and min(a[0], b[0]) < xc - w / 2 and max(a[0], b[0]) > xc + w / 2:
			s = 1 if b[0] > a[0] else -1
			n = [[xc - s * w / 2, ye], [xc - s * w / 2, ye - d], [xc + s * w / 2, ye - d], [xc + s * w / 2, ye]]
			return poly[:i + 1] + n + poly[i + 1:]
	raise ValueError('no straight ground edge across the notch')


def inside(pt, poly):
	x, y = pt
	r = False
	for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
		if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
			r = not r
	return r


def dist_edge(pt, poly):
	P = np.asarray(poly, float)
	B = np.roll(P, -1, axis=0)
	AB = B - P
	t = np.clip(((pt - P) * AB).sum(1) / np.maximum((AB * AB).sum(1), 1e-12), 0, 1)
	return float(np.min(np.linalg.norm(pt - (P + t[:, None] * AB), axis=1)))


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('out')
	ap.add_argument('--shape', default='disc')
	ap.add_argument('--d', type=float, default=30.0)
	ap.add_argument('--w', type=float, default=30.0)
	ap.add_argument('--h', type=float, default=30.0)
	ap.add_argument('--r', type=float, default=3.0)
	ap.add_argument('--clear', type=float, default=6.0)
	ap.add_argument('--layers', type=int, default=2)
	ap.add_argument('--t', type=float, default=1.0)
	ap.add_argument('--er', type=float, default=4.5)
	ap.add_argument('--tand', type=float, default=0.02)
	ap.add_argument('--battery', default='B')
	ap.add_argument('--bat', default='0,-2')
	ap.add_argument('--bat-rot', type=int, default=0)
	ap.add_argument('--site', type=float, default=-3.0)
	ap.add_argument('--mirror', action='store_true')
	ap.add_argument('--notch', default='')
	a = ap.parse_args()

	ol = outline_disc(a.d) if a.shape == 'disc' else outline_rect(a.w, a.h, a.r)
	top = max(p[1] for p in ol)
	ye = round(top - a.clear, 4)
	gnd = clip_below(ol, ye)
	if a.notch:
		w, d = (float(v) for v in a.notch.split(','))
		gnd = insert_notch(gnd, ye, a.site, w, d)

	if a.layers == 2:
		names = ['F.Cu', 'B.Cu']
		diel = [{'name': 'core', 'z0': 0.0, 'z1': a.t, 'er': a.er, 'tand': a.tand}]
		zc = {'F.Cu': a.t, 'B.Cu': 0.0}
	else:
		pp = 0.2104                        # JLC 4-layer 7628 prepreg, core fills the rest
		names = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
		diel = [{'name': 'prepreg1', 'z0': a.t - pp, 'z1': a.t, 'er': 4.4, 'tand': a.tand},
			{'name': 'core', 'z0': pp, 'z1': a.t - pp, 'er': a.er, 'tand': a.tand},
			{'name': 'prepreg2', 'z0': 0.0, 'z1': pp, 'er': 4.4, 'tand': a.tand}]
		zc = {'F.Cu': a.t, 'In1.Cu': a.t - pp, 'In2.Cu': pp, 'B.Cu': 0.0}
	stack = {'copper': {n: {'z': zc[n], 't': 0.035} for n in names}, 'dielectrics': diel}

	vias = []
	for x in np.arange(-a.d, a.d, 1.5):
		pt = np.array([x, ye - 0.6])
		if inside(pt, gnd) and dist_edge(pt, ol) > 0.8 and not (a.notch and abs(x - a.site) < 1.5):
			vias.append(pt)
	for x in np.arange(-a.d, a.d, 3.0):
		for y in np.arange(ye - 3.0, -a.d, -3.0):
			pt = np.array([x, y])
			if inside(pt, gnd) and dist_edge(pt, ol) > 0.8:
				vias.append(pt)
	vias = [{'x': round(float(v[0]), 4), 'y': round(float(v[1]), 4), 'drill': 0.3, 'd': 0.6, 'net': 'GND'} for v in vias]

	pads = {}
	if a.battery in ('B', 'F'):
		bx, by = (float(v) for v in a.bat.split(','))
		lst = []
		for num, (px, py), (sx, sy) in HOLDER_PADS:
			if a.bat_rot == 90:
				px, py, sx, sy = -py, px, sy, sx
			cx, cy = bx + px, by + py
			lst.append({'num': num, 'net': 'GND' if num == '2' else 'VDD', 'c': [cx, cy],
				'bbox': [cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2], 'layers': [a.battery + '.Cu']})
		pads['BT1'] = {'pos': [bx, by], 'rot': a.bat_rot, 'side': a.battery, 'pads': lst}

	board = {'source': 'synth_board.py ' + ' '.join('%s=%s' % kv for kv in vars(a).items() if kv[0] != 'out'),
		'origin_kicad': [150.0, 100.0], 'stackup': stack, 'outline': [ol], 'copper': {n: [gnd] for n in names},
		'vias': vias, 'pads': pads, 'battery': dict(CR1632) if pads else None,
		'site': {'x': a.site, 'y': ye, 'rot': 0, 'mirror': a.mirror}, 'ground_edge': ye, 'ae1': None}
	os.makedirs(a.out, exist_ok=True)
	p = os.path.join(a.out, 'board.json')
	json.dump(board, open(p, 'w'))
	print('wrote %s: %s, ground edge y %.2f, %d vias, battery %s' % (p, a.shape, ye, len(vias), a.battery))


if __name__ == '__main__':
	main()

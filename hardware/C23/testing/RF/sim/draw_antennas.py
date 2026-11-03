"""Draw the antennas of a case list on the board, in KiCad coordinates, to check what is simulated.

Each panel shows the board outline, the F.Cu ground copper, the vias (drill size), the antenna as it is built in
sim_board.py (antenna.rects, or the AE1 copper for "placed"), the J2 port position and the smallest distance
from the antenna copper to the board edge.

Usage: python draw_antennas.py cases/<list>.json [out.png]      (default out: results/plots/<list>_geometry.png)
"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import antenna as ant  # noqa: E402

DEFAULT_BOARD = 'build/board.json'


def kc(x, y):
	"""Simulation mm to KiCad mm (see export_board.py)."""
	return np.asarray(x) + 150.0, 100.0 - np.asarray(y)


def antenna_polys(case, board):
	a = case['antenna']
	if a == 'placed':
		return [np.array(p) for p in board['ae1']['copper']]
	r, _ = ant.rects(a)
	return [np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]) for (x0, y0, x1, y1) in r]


def seg_dist(p, a, b):
	ab = b - a
	t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
	return np.linalg.norm(p - (a + t * ab))


def edge_clearance(polys, outline):
	"""Smallest distance from any antenna polygon vertex or densified edge point to the board outline."""
	best = (1e9, None)
	ol = [np.array(o) for o in outline]
	for poly in polys:
		pts = []
		for a, b in zip(poly, np.roll(poly, -1, axis=0)):
			n = max(int(np.linalg.norm(b - a) / 0.05), 1)
			pts += [a + (b - a) * t for t in np.linspace(0, 1, n + 1)]
		for p in pts:
			for o in ol:
				for a, b in zip(o, np.roll(o, -1, axis=0)):
					d = seg_dist(p, a, b)
					if d < best[0]:
						best = (d, p)
	return best


def draw_panel(ax, case, board, title=None, full=False):
	"""One board + antenna panel. full=True shows the whole board, else the top part around the antenna."""
	for o in board['outline']:
		x, y = kc(*np.array(o).T)
		ax.add_patch(Polygon(np.c_[x, y], fill=False, ec='k', lw=1.2))
	for pts in board['copper']['F.Cu']:
		x, y = kc(*np.array(pts).T)
		ax.add_patch(Polygon(np.c_[x, y], fc='#c87533', ec='none', alpha=0.55))
	for v in board['vias']:
		x, y = kc(v['x'], v['y'])
		ax.add_patch(plt.Circle((x, y), v['drill'] / 2, fc='k'))
	polys = antenna_polys(case, board)
	for poly in polys:
		x, y = kc(*poly.T)
		ax.add_patch(Polygon(np.c_[x, y], fc='#2f5fd0', ec='#123', lw=0.6, alpha=0.9))
	for ref, col in (('J2', 'm'), ('L2', 'g'), ('L3', 'g')):
		if ref not in board['pads']:
			continue
		for p in board['pads'][ref]['pads']:
			if ref == 'J2' and p['num'] != '1':
				continue
			x0, y0, x1, y1 = p['bbox']
			(a, b), (c, d) = kc(x0, y0), kc(x1, y1)
			ax.add_patch(Rectangle((a, d), c - a, b - d, fc=col, ec='none', alpha=0.8))
	dmin, pmin = edge_clearance(polys, board['outline'])
	x, y = kc(*pmin)
	ax.plot(x, y, 'r+', ms=12, mew=2)
	allp = np.vstack(polys)
	X, Y = kc(allp[:, 0], allp[:, 1])
	desc = 'AE1 copper from the board file' if case['antenna'] == 'placed' else ant.describe(case['antenna'])
	sub = 'antenna x %.2f..%.2f, y %.2f..%.2f, min. edge clearance %.2f mm (red +)' % (X.min(), X.max(), Y.min(), Y.max(), dmin)
	ax.set_title('\n'.join([title or '', desc, sub]), fontsize=8)
	ol = np.vstack([np.array(o) for o in board['outline']])
	ox, oy = kc(ol[:, 0], ol[:, 1])
	ax.set_xlim(ox.min() - 2, ox.max() + 2)
	ax.set_ylim(oy.max() + 1 if full else min(oy.max() + 1, 97), oy.min() - 2)      # KiCad y grows downwards
	ax.set_aspect('equal')
	ax.grid(alpha=0.3)
	ax.tick_params(labelsize=7)
	return {'x': [float(X.min()), float(X.max())], 'y': [float(Y.min()), float(Y.max())], 'edge_clearance': float(dmin)}


def main():
	lst = json.load(open(sys.argv[1]))
	name = os.path.splitext(os.path.basename(sys.argv[1]))[0]
	out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'results', 'plots', name + '_geometry.png')
	os.makedirs(os.path.dirname(out), exist_ok=True)
	n = len(lst)
	cols = 2 if n > 1 else 1
	rows = int(np.ceil(n / cols))
	fig, axs = plt.subplots(rows, cols, figsize=(8 * cols, 5.2 * rows), squeeze=False)
	for k, item in enumerate(lst):
		case = item['case']
		board = json.load(open(os.path.join(HERE, case.get('board', DEFAULT_BOARD))))
		draw_panel(axs[k // cols][k % cols], case, board, item['name'])
	for k in range(n, rows * cols):
		axs[k // cols][k % cols].axis('off')
	fig.suptitle('%s: simulated antennas in KiCad coordinates (mm). Blue = antenna, brown = F.Cu ground, '
		'magenta = J2 pad 1 (port), green = L2/L3 pads' % name, fontsize=9)
	fig.tight_layout()
	fig.savefig(out, dpi=110)
	plt.close(fig)
	print('wrote', out)


if __name__ == '__main__':
	main()

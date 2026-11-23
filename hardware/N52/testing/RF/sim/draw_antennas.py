"""Draw the antennas of a case list on their boards, in KiCad coordinates, to check what is simulated.

Each panel: board outline, F.Cu ground (brown), vias, the antenna keep-out cut from every layer (dashed), the
antenna (blue), the port (red), the CR1632 cell outline (grey dashed), the smallest antenna-to-edge distance (+).

Usage: python draw_antennas.py cases/<list>.json [out.png]      (default out: results/plots/<list>_geometry.png)
"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import antenna as ant  # noqa: E402


def kc(board, x, y):
	ox, oy = board.get('origin_kicad', [150.0, 100.0])
	return np.asarray(x) + ox, oy - np.asarray(y)


def rect_patch(board, r, **kw):
	(a, b), (c, d) = [kc(board, r[0], r[1]), kc(board, r[2], r[3])]
	return Rectangle((a, d), c - a, b - d, **kw)


def draw_panel(ax, case, board, title=None, zoom=False):
	a = case['antenna']
	for o in board['outline']:
		x, y = kc(board, *np.array(o).T)
		ax.add_patch(Polygon(np.c_[x, y], fill=False, ec='k', lw=1.2))
	for pts in board['copper'].get('F.Cu', []):
		x, y = kc(board, *np.array(pts).T)
		ax.add_patch(Polygon(np.c_[x, y], fc='#c87533', ec='none', alpha=0.45))
	trace = case.get('ports', 'feed') == 'trace'
	cuts = ant.clear_rects(a, board, notch=not trace)
	for r in cuts:
		ax.add_patch(rect_patch(board, r, fc='white', ec='#666', ls='--', lw=0.7))
	for v in board['vias']:
		if any(r[0] <= v['x'] <= r[2] and r[1] <= v['y'] <= r[3] for r in cuts):
			continue
		x, y = kc(board, v['x'], v['y'])
		ax.add_patch(Circle((x, y), v['drill'] / 2, fc='k'))
	bt = board.get('pads', {}).get('BT1')
	if bt and board.get('battery') and case.get('battery', True):
		pp = [p['c'] for p in bt['pads'] if p['num'] == '1']
		x, y = kc(board, (pp[0][0] + pp[1][0]) / 2, (pp[0][1] + pp[1][1]) / 2)     # cell centre, as in sim_board
		ax.add_patch(Circle((x, y), board['battery']['d'] / 2, fill=False, ec='#777', ls='--', lw=1))
		ax.text(x, y, 'CR1632 (%s side)' % bt['side'], ha='center', va='center', fontsize=7, color='#777', clip_on=True)
	rects, q = ant.rects(a, board)
	for r in rects:
		ax.add_patch(rect_patch(board, r, fc='#2f5fd0', ec='none', alpha=0.95))
	if board.get('ae1') and board['ae1'].get('copper'):          # AE1 footprint copper on the board, for comparison
		for pts in board['ae1']['copper']:
			x, y = kc(board, *np.array(pts).T)
			ax.add_patch(Polygon(np.c_[x, y], fill=False, ec='#0a0', lw=1.0, ls='-'))
	if trace:                                  # footprint feed pad, and the two sub-ports across the trace gaps
		ax.add_patch(rect_patch(board, ant.feed_pad_rect(a, board), fc='#2f5fd0', ec='none'))
		tp = case.get('trace_port')
		if tp is None:
			import feedport
			tp = feedport.trace_port(board, a)
		g0, t0, t1, g1 = tp['x']
		for x0, x1 in ((g0, t0), (t1, g1)):
			ax.add_patch(rect_patch(board, (x0, tp['y'] - tp['len'] / 2, x1, tp['y'] + tp['len'] / 2), fc='r', ec='none'))
	else:
		ax.add_patch(rect_patch(board, ant.port_tab_rect(a, board), fc='#2f5fd0', ec='none'))
		ps, pe, _ = ant.port_line(a, board)
		ax.add_patch(rect_patch(board, (min(ps[0], pe[0]), min(ps[1], pe[1]), max(ps[0], pe[0]), max(ps[1], pe[1])), fc='r', ec='none'))
	ol = board['outline'][0]
	boxes = [r for r in rects]
	d, pt = ant.edge_clearance(boxes, ol)
	x, y = kc(board, *pt)
	ax.plot(x, y, 'm+', ms=12, mew=2)
	allr = np.array(rects)
	X0, Y1 = kc(board, allr[:, 0].min(), allr[:, 1].min())
	X1, Y0 = kc(board, allr[:, 2].max(), allr[:, 3].max())
	sz = ant.size(a)
	errs = ant.check(a, board)
	sub = 'copper x %.2f..%.2f, y %.2f..%.2f (KiCad), %.1f x %.1f mm, edge clearance %.2f mm%s' % (
		X0, X1, Y0, Y1, sz['w'], sz['h'], d, ('\nRULES: ' + '; '.join(errs)) if errs else '')
	ax.set_title('\n'.join([t for t in (title, ant.describe(a), sub) if t]), fontsize=7.5, color='r' if errs else 'k')
	o = np.array(ol)
	ox, oy = kc(board, o[:, 0], o[:, 1])
	if zoom:
		k = cuts[0]
		(zx0, zy1), (zx1, zy0) = kc(board, k[0] - 2, k[1] - (6 if trace else 3)), kc(board, k[2] + 2, k[3] + 2)
		ax.set_xlim(zx0, zx1)
		ax.set_ylim(zy1, zy0)
	else:
		ax.set_xlim(ox.min() - 1.5, ox.max() + 1.5)
		ax.set_ylim(oy.max() + 1.5, oy.min() - 1.5)       # KiCad y grows downwards
	ax.set_aspect('equal')
	ax.grid(alpha=0.3)
	ax.tick_params(labelsize=7)
	return {'x': [float(X0), float(X1)], 'y': [float(Y0), float(Y1)], 'edge_clearance': float(d)}


def main():
	lst = json.load(open(sys.argv[1]))
	name = os.path.splitext(os.path.basename(sys.argv[1]))[0]
	out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'results', 'plots', name + '_geometry.png')
	os.makedirs(os.path.dirname(out), exist_ok=True)
	n = len(lst)
	cols = min(n, 3)
	rows = int(np.ceil(n / cols))
	fig, axs = plt.subplots(rows, cols * 2, figsize=(5.2 * cols * 2, 5.0 * rows), squeeze=False)
	boards = {}
	for k, item in enumerate(lst):
		c = item['case']
		b = boards.setdefault(c['board'], json.load(open(os.path.join(HERE, c['board']))))
		r, cc = k // cols, (k % cols) * 2
		draw_panel(axs[r][cc], c, b, item.get('name'))
		draw_panel(axs[r][cc + 1], c, b, 'zoom', zoom=True)
	for k in range(n, rows * cols):
		axs[k // cols][(k % cols) * 2].axis('off')
		axs[k // cols][(k % cols) * 2 + 1].axis('off')
	fig.suptitle('%s: simulated antennas, KiCad coordinates (mm). Blue antenna, red port, brown F.Cu ground, '
		'dashed = keep-out cut from every copper layer, green outline = AE1 footprint copper in the board file' % name, fontsize=9)
	fig.tight_layout()
	fig.savefig(out, dpi=100)
	plt.close(fig)
	print('wrote', out)


if __name__ == '__main__':
	main()

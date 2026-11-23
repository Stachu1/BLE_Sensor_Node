"""Plot the copper of an exported board per layer (KiCad coordinates), with vias, the BT1 pads (net names) and the
battery parts as sim_board.py builds them. Used to check what is electrically connected in the model: the export
turns every copper item of every net into metal, and no component is modelled (a capacitor is an open circuit).

Usage: python draw_layers.py build/<rev>/board.json [out.png]
"""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Polygon, Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def main():
	bp = sys.argv[1]
	board = json.load(open(bp))
	ox, oy = board['origin_kicad']
	kc = lambda x, y: (x + ox, oy - y)      # noqa: E731
	out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'results', 'plots',
		os.path.basename(os.path.dirname(bp)) + '_layers.png')
	layers = list(board['copper'])
	fig, axs = plt.subplots(1, len(layers), figsize=(7 * len(layers), 6.5))
	bt = board.get('pads', {}).get('BT1')
	for ax, name in zip(axs, layers):
		for poly in board['outline']:
			ax.add_patch(Polygon([kc(*p) for p in poly], closed=True, fill=False, ec='k', lw=1))
		for poly in board['copper'][name]:
			pts = poly['outer'] if isinstance(poly, dict) else poly
			ax.add_patch(Polygon([kc(*p) for p in pts], closed=True, fc='#c87533', ec='#7a4a1f', lw=0.4, alpha=0.8))
			for h in (poly.get('holes', []) if isinstance(poly, dict) else []):
				ax.add_patch(Polygon([kc(*p) for p in h], closed=True, fc='w', ec='#7a4a1f', lw=0.4))
		for v in board.get('vias', []):
			ax.add_patch(Circle(kc(v['x'], v['y']), v['d'] / 2, fc='k'))
			ax.text(*kc(v['x'], v['y'] - 0.6), v.get('net', ''), fontsize=6, ha='center', va='top')
		if bt:
			pp = [p['c'] for p in bt['pads'] if p['num'] == '1']
			cx, cy = (pp[0][0] + pp[1][0]) / 2, (pp[0][1] + pp[1][1]) / 2
			ax.add_patch(Circle(kc(cx, cy), board['battery']['d'] / 2, fill=False, ec='b', ls='--', lw=1))
			for p in bt['pads']:
				x0, y0, x1, y1 = p['bbox']
				a, b = kc(x0, y1)
				ax.add_patch(Rectangle((a, b), x1 - x0, y1 - y0, fill=False, ec='b', lw=1))
				ax.text(*kc(*p['c']), '%s\n%s' % (p['num'], p['net']), fontsize=6, ha='center', va='center', color='b')
		ax.set_title('%s  (%s)' % (name, os.path.basename(os.path.dirname(bp))))
		ax.set_aspect('equal')
		ax.autoscale_view()
		ax.invert_yaxis()
		ax.grid(alpha=0.3)
	fig.suptitle('copper as exported (all nets are metal, parts are not modelled), vias black, BT1 pads / cell blue')
	fig.tight_layout()
	fig.savefig(out, dpi=110)
	print(out)


if __name__ == '__main__':
	main()

"""Plot board.json copper per layer with a candidate antenna and the ports, to check the model by eye.

Usage: python preview.py [board.json] [out.png] [antenna-json]
"""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import antenna as ant  # noqa: E402
import sim_ports  # noqa: E402


def main():
	bj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'build', 'board.json')
	out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'build', 'preview.png')
	a = json.loads(sys.argv[3]) if len(sys.argv) > 3 else ant.placed_r011()
	b = json.load(open(bj))
	fig, axs = plt.subplots(2, 3, figsize=(18, 12))
	views = [('F.Cu', (-17.5, 17.5, -17.5, 17.5)), ('In1.Cu', (-17.5, 17.5, -17.5, 17.5)),
		('In2.Cu', (-17.5, 17.5, -17.5, 17.5)), ('B.Cu', (-17.5, 17.5, -17.5, 17.5)),
		('F.Cu', (-12, 12, 1, 17.5)), ('F.Cu', (-8, -3.5, 2, 11.5))]
	for ax, (name, lim) in zip(axs.flat, views):
		for o in b['outline']:
			ax.add_patch(Polygon(o, fill=False, ec='k'))
		for pts in b['copper'][name]:
			ax.add_patch(Polygon(pts, fc='#c87533', ec='#804000', lw=0.3, alpha=0.7))
		if name == 'F.Cu':
			for (x0, y0, x1, y1) in ant.rects(a)[0]:
				ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='#3060c0', alpha=0.7))
			for gname, subs in sim_ports.port_defs(b, 'multi', 0):
				for s, e, d, R in subs:
					ax.add_patch(Rectangle((min(s[0], e[0]), min(s[1], e[1])), abs(e[0] - s[0]), abs(e[1] - s[1]),
						fc='red', alpha=0.8))
					ax.text(e[0], e[1], gname, fontsize=7, color='red')
		for v in b['vias']:
			ax.add_patch(plt.Circle((v['x'], v['y']), v['d'] / 2, fc='k'))
		ax.set_xlim(lim[0], lim[1])
		ax.set_ylim(lim[2], lim[3])
		ax.set_aspect('equal')
		ax.grid(alpha=0.3)
		ax.set_title(name + ('  ' + ant.describe(a) if name == 'F.Cu' else ''), fontsize=9)
	fig.tight_layout()
	fig.savefig(out, dpi=110)
	print('wrote', out)


if __name__ == '__main__':
	main()

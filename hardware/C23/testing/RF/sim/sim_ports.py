"""Port and pad helpers for sim_board.py (no openEMS import, so preview.py can use them)."""
import numpy as np

import antenna as ant


def pad(board, ref, num, net=None, near=None):
	c = [p for p in board['pads'][ref]['pads'] if p['num'] == num and (net is None or p['net'] == net)]
	if near is not None:
		c.sort(key=lambda p: np.hypot(p['c'][0] - near[0], p['c'][1] - near[1]))
	return c[0]


def port_defs(board, mode, zF):
	"""Port groups: list of (name, [(start, stop, dir, R)]). A group with several sub-ports is one port of
	50 ohm made of parallel sub-ports (voltage averaged, currents summed)."""
	if mode == 'notch':
		return [('feed', [([ant.FEED_X - 0.5, ant.GND_Y - 1, zF], [ant.FEED_X + 0.5, ant.GND_Y, zF], 'y', 50)])]
	p1 = pad(board, 'J2', '1')
	b = p1['bbox']
	yov = None
	subs = []
	for side in (-1, 1):
		g = sorted([p for p in board['pads']['J2']['pads'] if p['num'] == '3' and np.sign(p['c'][0] - p1['c'][0]) == side],
			key=lambda p: abs(p['c'][1] - p1['c'][1]))[0]
		gb = g['bbox']
		y0, y1 = max(b[1], gb[1]), min(b[3], gb[3])
		gx = gb[2] if side < 0 else gb[0]
		px = b[0] if side < 0 else b[2]
		subs.append(([gx, y0, zF], [px, y1, zF], 'x', 100))
	groups = [('J2', subs)]
	if mode == 'multi':
		a, c = pad(board, 'L2', '1')['bbox'], pad(board, 'L2', '2')['bbox']
		lo, hi = (a, c) if a[1] < c[1] else (c, a)
		groups.append(('L2', [([max(a[0], c[0]), lo[3], zF], [min(a[2], c[2]), hi[1], zF], 'y', 50)]))
		for ref, sig in (('L3', '2'), ('L4', '1')):
			s = pad(board, ref, sig)['bbox']
			g = pad(board, ref, '1' if sig == '2' else '2')['bbox']
			y0, y1 = max(s[1], g[1]), min(s[3], g[3])
			if g[0] > s[2]:
				groups.append((ref, [([g[0], y0, zF], [s[2], y1, zF], 'x', 50)]))
			else:
				groups.append((ref, [([g[2], y0, zF], [s[0], y1, zF], 'x', 50)]))
	return groups

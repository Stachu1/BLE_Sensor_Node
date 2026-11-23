"""The "trace" port: where the antenna is driven when the feed trace is routed on the board (pure numpy).

Why: with a routed feed trace the trace runs up to the antenna in a gap of the ground pour (a coplanar line). The old
"feed" port across the notch then has the trace, not the ground, at its lower end (found on r2, 2026-11-14), and the
real antenna is driven at the end of the matching network anyway. So the port goes there: across the two gaps
between the feed-net pad of the part nearest to the antenna (L1) and the pour on both sides of it (r4, 2026-11-14:
L1 sits 0.2 mm below the antenna feed pad, there is no straight trace left to put the port on). Two sub-ports of 100 ohm in parallel (voltage averaged, currents summed) = one 50 ohm port whose
reference plane is the end of the matching network. The trace and the antenna feed pad are part of the model, so
the impedance includes the feed trace, and no notch is needed.

trace_port(board, a) returns the case entry {"y", "x": [g0, t0, t1, g1], "len", "part"}: sub-port 1 spans x g0..t0
(left ground edge to the left trace edge), sub-port 2 spans t1..g1, both over y - len/2 .. y + len/2 on F.Cu.
Only for a trace that runs along y (antenna rot 0 or 180) for now.

Usage: python feedport.py build/<rev>/board.json      prints the port for the board's AE1 site
"""
import json
import sys

import numpy as np

import antenna as ant


def inside(pt, poly):
	x, y = pt
	p = np.asarray(poly)
	x0, y0 = p[:, 0], p[:, 1]
	x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
	c = ((y0 > y) != (y1 > y)) & (x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-300) + x0)
	return bool(np.count_nonzero(c) % 2)


def copper_at(board, layer, x, y):
	return any(inside((x, y), poly) for poly in board['copper'][layer])


def scan(board, layer, y, x0, x1, step=0.01):
	"""Copper runs along the line y between x0 and x1: list of (start, end)."""
	xs = np.arange(x0, x1 + step / 2, step)
	cu = [copper_at(board, layer, x, y) for x in xs]
	runs, start = [], None
	for x, c in zip(xs, cu):
		if c and start is None:
			start = x
		if not c and start is not None:
			runs.append((round(start, 3), round(x - step, 3)))
			start = None
	if start is not None:
		runs.append((round(start, 3), round(xs[-1], 3)))
	return runs


def trace_port(board, a=None, length=0.4, ref=None, net=None):
	"""ref / net (optional): put the port beside the pad of part ref on net instead (e.g. L2 on the radio side, so the
	whole matching network with real parts is inside the model, r7 2026-11-15)."""
	s = ant.site(a or {}, board)
	if s['rot'] % 180:
		raise SystemExit('trace port: only a feed trace along y (antenna rot 0 / 180) is supported')
	feed = board.get('feed') or {}
	net = net or feed.get('net')
	cands = []
	for ref in ([ref] if ref else feed.get('parts', [])):
		for p in board['pads'][ref]['pads']:
			if p['net'] == net:
				cands.append((abs(p['c'][1] - s['y']) + abs(p['c'][0] - s['x']), ref, p))
	if not cands:
		raise SystemExit('trace port: no part on the feed net %r in board.json (re-export with the new export_board.py)' % net)
	_, ref, p = min(cands, key=lambda c: c[0])
	b = p['bbox']
	length = min(length, 0.7 * (b[3] - b[1]))           # beside the pad, clear of its rounded corners
	y = p['c'][1]
	runs = scan(board, 'F.Cu', y, p['c'][0] - 3.0, p['c'][0] + 3.0)
	tr = [r for r in runs if r[0] <= p['c'][0] <= r[1]]
	if not tr:
		raise SystemExit('trace port: no trace at y %.2f above %s' % (y, ref))
	t0, t1 = tr[0]
	left = [r for r in runs if r[1] < t0]
	right = [r for r in runs if r[0] > t1]
	if not left or not right or t1 - t0 > 1.5:
		raise SystemExit('trace port: expected ground | gap | trace | gap | ground at y %.2f, got %s' % (y, runs))
	g0, g1 = left[-1][1], right[0][0]
	for yy in (y - length / 2, y + length / 2):        # the gaps must be straight over the port length
		r2 = scan(board, 'F.Cu', yy, g0 - 0.2, g1 + 0.2)
		if len(r2) != 3 or abs(r2[1][0] - t0) > 0.03 or abs(r2[1][1] - t1) > 0.03:
			raise SystemExit('trace port: the gaps are not straight over the port length at y %.2f: %s' % (yy, r2))
	return {'y': round(float(y), 3), 'x': [round(float(v), 3) for v in (g0, t0, t1, g1)], 'len': length, 'part': ref}


if __name__ == '__main__':
	bd = json.load(open(sys.argv[1]))
	print(json.dumps(trace_port(bd)))

"""Parametric meandered inverted-F antenna (MIFA) for the BSN-N52 board sims. Pure numpy, runs on both machines.

An antenna is a list of axis-aligned rectangles on F.Cu (their union is the copper), built in a LOCAL frame and
then placed on the board at a SITE.

Local frame (mm): the ground edge is the line v = 0, ground below (v < 0). The feed leg centre is at u = 0.
The antenna runs towards +u (mirror flips it to -u). The short leg is at u = -S.

        v ^      <---- A ---->  P
        H |  +-----------------+   +---+   +--   arm and top links, trace width W
          |  |  |              |   |   |   |
          |  |  |              |   |   |   |      fingers 1..n (odd go down, even go up)
        G |  |  |              +---+   +---+      bottom links (bottom edge at v = G)
        0 +--+--+---------------------------- ground edge
             S  feed (port in the notch below, v = -Nd .. 0)

Parameters (family "mifa", all mm except n)
    W   trace width of arm, fingers and links        Wf  feed leg width       Ws  short leg width
    S   short-to-feed spacing, centre to centre      H   ground edge to the top edge of the arm (total height)
    A   feed leg centre to the centre of finger 1    G   ground edge to the bottom edge of the bottom links
    n   number of meander fingers, a float: n = 3.4 is 3 full fingers plus 40 % of the path (link + finger) to
        the end of a fourth one, the link grows first. Length and copper are continuous in n (the tuner needs
        that). n = 0 is a plain IFA with the arm ending at u = A.
    P   finger pitch, centre to centre
    Nd, Nw  feed notch depth and width in the ground (the port sits across it)
    K   keep-out margin around the antenna when there is no fixed keep-out (copper is cut from every layer in the
        antenna bounding box + K, see clear_rects)

Family "fmifa" (folded-back IFA, added 2026-11-14 for the 24 x 20 mm board r2 where the arm runs into the right edge):
the arm runs to u = A, drops by D (centre line to centre line) and runs back towards the feed for R (centre-line
length from the drop centre to the open end, the tuning parameter). No fingers, so less copper close to the ground
than a meander of the same length:

        v ^      <------ A ------>
        H |  +----------------------+     arm (width W)
          |  |  |       +-----------+ D   return row (width W), open end at u = A - R
          |  |  |
        0 +--+--+----------------------- ground edge
    parameters W, Wf, Ws, S, H, A, D, R, Nd, Nw, K (G, n, P do not exist).

Keep-out: "keepout": {"u0", "w", "h", "m"} in the antenna dict fixes the region instead (local frame: u0 .. u0 + w,
v = 0 .. h). The board copper is cut from exactly this box (and the notch), and every antenna copper edge has to stay
m inside it (check). This is the footprint's fixed interface to the board: origin (feed point), keep-out and notch
stay where they are, tuning only changes the copper inside, so a new tune never moves anything on the PCB.
GENERIC_KEEPOUT is the one of the generic BSN-N52 footprint (gen_mifa_footprint.py --generic).

Site: {"x", "y", "rot", "mirror"} in simulation coordinates, the feed point on the ground edge. rot is a multiple
of 90 degrees (counter-clockwise), the local +v (away from the ground) maps to (-sin rot, cos rot). Every
board.json carries a default site (synth_board.py or export_board.py from the AE1 footprint), a case can override
it with "site" inside the antenna dict.
"""
import math

import numpy as np

EDGE_MARGIN = 0.4      # copper to board edge
MIN_GAP = 0.25         # copper to copper inside the antenna (JLC standard 0.1 mm, kept wide for etch tolerance)
SHORT_GAP = 0.575                            # short leg to feed leg, edge to edge (user rule 2026-11-15)
OVERLAP = 0.25         # short leg reaches this far into the ground

DEFAULTS = {
	'mifa': {'W': 0.5, 'Wf': 0.5, 'Ws': 0.5, 'S': 1.6, 'H': 4.0, 'A': 2.4, 'G': 1.0, 'n': 4.0, 'P': 1.2,
		'Nd': 1.0, 'Nw': 1.0, 'K': 1.0},
	'fmifa': {'W': 0.5, 'Wf': 0.5, 'Ws': 0.5, 'S': 1.0, 'H': 4.6, 'A': 12.0, 'D': 1.5, 'R': 2.0,
		'Nd': 1.0, 'Nw': 1.0, 'K': 1.0},
}
PARAMS = list(DEFAULTS['mifa'])
KEEP_KEYS = ('family', 'site', 'keepout')      # non-parameter keys of an antenna dict that belong to the case

# Generic BSN-N52 footprint: 24 x 5 mm keep-out = the full PCB width (user, 2026-11-14), feed 8 mm from its left edge,
# so with AE1 at (146.0, 93.0) the feed sits straight above L1 (x 146.0, the RF chain the user placed) and the keep-out
# covers the board from edge to edge (x 138..162) and up to the top edge (y 88..93). The arm can run about 15.5 mm to
# the right, copper 0.3 mm inside the keep-out. (First version: feed 5 mm from the left edge, cases/keepout24.json.)
GENERIC_KEEPOUT = {'u0': -8.0, 'w': 24.0, 'h': 5.0, 'm': 0.3}
# starting copper inside it (not tuned yet): straight IFA (n = 0), arm 4.5 mm high
GENERIC = {'family': 'mifa', 'W': 0.5, 'S': 2.5, 'H': 4.5, 'A': 13.0, 'G': 1.0, 'P': 1.0, 'n': 0.0,
	'keepout': GENERIC_KEEPOUT}


def params(p):
	q = dict(DEFAULTS[p.get('family', 'mifa')])
	q.update({k: v for k, v in p.items() if k in q})
	return q


# ---------------------------------------------------------------------------------------------------- local frame
def local_rects(p):
	"""Antenna copper in the local frame: list of (u0, v0, u1, v1, tag)."""
	q = params(p)
	if p.get('family') == 'fmifa':
		W, Wf, Ws, S, H, A, D, R = (q[k] for k in ('W', 'Wf', 'Ws', 'S', 'H', 'A', 'D', 'R'))
		vr = H - W / 2 - D                       # return row centre line
		return [(-S - Ws / 2, -OVERLAP, -S + Ws / 2, H, 'short'),
			(-Wf / 2, 0.0, Wf / 2, H - W, 'feed'),
			(-S - Ws / 2, H - W, A + W / 2, H, 'arm'),
			(A - W / 2, vr - W / 2, A + W / 2, H - W, 'drop'),
			(A - R, vr - W / 2, A + W / 2, vr + W / 2, 'return')], q
	W, Wf, Ws, S, H, A, G, n, P = (q[k] for k in ('W', 'Wf', 'Ws', 'S', 'H', 'A', 'G', 'n', 'P'))
	us = -S
	r = [(us - Ws / 2, -OVERLAP, us + Ws / 2, H, 'short'),
		(-Wf / 2, 0.0, Wf / 2, H - W, 'feed')]
	nf = int(math.ceil(n - 1e-9))
	if nf == 0:
		r.append((us - Ws / 2, H - W, A, H, 'arm'))
		return r, q
	r.append((us - Ws / 2, H - W, A + W / 2, H, 'arm'))
	hc = H - G - W                               # finger centre-line length
	for k in range(1, nf + 1):
		frac = min(n - (k - 1), 1.0)
		uc = A + (k - 1) * P
		down = k % 2 == 1
		lf = frac * hc                           # centre-line length of this finger
		if k > 1:                                # link from finger k-1 to finger k, grows first (n continuous)
			ll = min(frac * (P + hc), P)
			lf = frac * (P + hc) - ll
			if not down:                         # finger k-1 went down and ended at the bottom
				r.append((uc - P - W / 2, G, uc - P + ll + W / 2, G + W, 'link'))
			else:
				r.append((uc - P - W / 2, H - W, uc - P + ll + W / 2, H, 'link'))
			if lf <= 1e-9:
				break
		if down:
			r.append((uc - W / 2, H - W - lf, uc + W / 2, H, 'finger'))
		else:
			r.append((uc - W / 2, G, uc + W / 2, G + W + lf, 'finger'))
	return r, q


def local_notch(q):
	return (-q['Nw'] / 2, -q['Nd'], q['Nw'] / 2, 0.0)


def local_bbox(p):
	r, q = local_rects(p)
	a = np.array([b[:4] for b in r])
	return float(a[:, 0].min()), 0.0, float(a[:, 2].max()), float(a[:, 3].max())


def length(p):
	"""Centre-line length from the short leg foot along the arm and the meander to the open end (mm)."""
	r, q = local_rects(p)
	if p.get('family') == 'fmifa':
		return (q['H'] - q['W'] / 2) + q['S'] + q['A'] + q['D'] + q['R']
	W, S, H, A, G, n, P = (q[k] for k in ('W', 'S', 'H', 'A', 'G', 'n', 'P'))
	L = (H - W / 2)                              # short leg up to the arm centre line
	if n <= 0:
		return L + S + A
	L += S + A                                   # arm to finger 1
	hc = (H - W / 2) - (G + W / 2)               # finger centre-line height
	nf = int(math.ceil(n - 1e-9))
	for k in range(1, nf + 1):
		frac = min(n - (k - 1), 1.0)
		L += frac * hc if k == 1 else frac * (P + hc)
	return L


# ---------------------------------------------------------------------------------------------------- placement
def site(p, board):
	s = dict(board.get('site') or {})
	s.update(p.get('site', {}))
	return {'x': float(s.get('x', 0.0)), 'y': float(s.get('y', 0.0)), 'rot': int(s.get('rot', 0)) % 360,
		'mirror': bool(s.get('mirror', False))}


def to_sim(u, v, s):
	u = -np.asarray(u, float) if s['mirror'] else np.asarray(u, float)
	v = np.asarray(v, float)
	c, sn = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[s['rot']]
	return s['x'] + c * u - sn * v, s['y'] + sn * u + c * v


def place(box, s):
	u0, v0, u1, v1 = box[:4]
	x, y = to_sim([u0, u1], [v0, v1], s)
	return (round(float(min(x)), 4), round(float(min(y)), 4), round(float(max(x)), 4), round(float(max(y)), 4))


def rects(p, board):
	"""Antenna copper in simulation coordinates: list of (x0, y0, x1, y1), and the full parameters."""
	r, q = local_rects(p)
	s = site(p, board)
	return [place(b, s) for b in r], q


def notch_rect(p, board):
	return place(local_notch(params(p)), site(p, board))


def clear_rects(p, board, notch=True):
	"""Regions cut from the board copper on every layer: the antenna bounding box plus K (from the ground edge
	up) and the feed notch. On the real board the AE1 footprint keep-out does the same. notch=False for the
	"trace" port: the routed feed trace and its gap in the pour come from the board copper and must not be cut."""
	q = params(p)
	s = site(p, board)
	k = p.get('keepout')
	if k:
		box = place((k['u0'], 0.0, k['u0'] + k['w'], k['h']), s)
	else:
		u0, _, u1, v1 = local_bbox(p)
		box = place((u0 - q['K'], 0.0, u1 + q['K'], v1 + q['K']), s)
	return [box, notch_rect(p, board)] if notch else [box]


PAD_W = 0.5                                  # MIFA_2G4 pad 1 width (feed pad, user footprint of 2026-11-14)


def feed_pad_rect(p, board):
	"""Footprint pad 1 (feed) below the feed leg, v = -Nd .. 0, for the "trace" port: the routed feed trace ends on
	it (the footprint pad is not in the exported board copper, export_board.py leaves AE1 out)."""
	q = params(p)
	w = min(q['Wf'], PAD_W)                  # the pad keeps the footprint width when the feed leg above it is wider
	return place((-w / 2, -q['Nd'], w / 2, 0.0), site(p, board))


def port_tab_rect(p, board):
	"""Copper tab of the feed width from the notch bottom 0.5 mm into the ground. On a real board the pour keeps its
	clearance from the feed pad, so the notch bottom sits lower than the footprint notch (b1: 0.25 mm) and the port's
	ground end would hang in a gap (2026-11-14: S11 -0.2 dB on every real-board run). The tab stands for the feed trace
	landing at the notch bottom and joins the port to the ground. On synthetic boards it overlaps the ground."""
	q = params(p)
	return place((-q['Wf'] / 2, -q['Nd'] - 0.5, q['Wf'] / 2, -q['Nd']), site(p, board))


def port_line(p, board):
	"""Lumped port across the notch: start (on the notch bottom, ground) and stop (feed leg foot) and direction."""
	q = params(p)
	s = site(p, board)
	x0, y0 = to_sim([-q['Wf'] / 2], [-q['Nd']], s)
	x1, y1 = to_sim([q['Wf'] / 2], [0.0], s)
	d = 'y' if s['rot'] in (0, 180) else 'x'
	return [float(x0[0]), float(y0[0])], [float(x1[0]), float(y1[0])], d


# ---------------------------------------------------------------------------------------------------- checks
def _inside(pt, poly):
	x, y = pt
	inside = False
	for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
		if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
			inside = not inside
	return inside


def _edge_dist(pt, poly):
	P = np.asarray(poly, float)
	A, B = P, np.roll(P, -1, axis=0)
	AB = B - A
	t = np.clip(((pt - A) * AB).sum(1) / np.maximum((AB * AB).sum(1), 1e-12), 0, 1)
	return float(np.min(np.linalg.norm(pt - (A + t[:, None] * AB), axis=1)))


def edge_points(box, step=0.1):
	x0, y0, x1, y1 = box
	nx, ny = max(int((x1 - x0) / step), 1), max(int((y1 - y0) / step), 1)
	xs, ys = np.linspace(x0, x1, nx + 1), np.linspace(y0, y1, ny + 1)
	return np.vstack([np.c_[xs, np.full_like(xs, y0)], np.c_[xs, np.full_like(xs, y1)],
		np.c_[np.full_like(ys, x0), ys], np.c_[np.full_like(ys, x1), ys]])


def edge_clearance(boxes, outline):
	best = (1e9, None)
	for b in boxes:
		for pt in edge_points(b):
			d = _edge_dist(pt, outline)
			if not _inside(pt, outline):
				d = -d
			if d < best[0]:
				best = (d, pt)
	return best


def check(p, board=None):
	"""Geometry rules. Without a board only the antenna itself is checked."""
	r, q = local_rects(p)
	e = []
	fm = p.get('family') == 'fmifa'
	if fm:
		W, Wf, Ws, S, H, A, D, R = (q[k] for k in ('W', 'Wf', 'Ws', 'S', 'H', 'A', 'D', 'R'))
		G, n, P = H - W / 2 - D - W / 2, 0.0, 1.0       # G = bottom edge of the return row
		if D - W < MIN_GAP - 1e-9:
			e.append('return row too close to the arm (D - W < %.2f)' % MIN_GAP)
		if G < MIN_GAP + 0.05:
			e.append('return row closer than %.2f mm to the ground edge' % (MIN_GAP + 0.05))
		if A - R < Wf / 2 + MIN_GAP - 1e-9:
			e.append('return row runs into the feed leg')
		if R < W / 2:
			e.append('R shorter than W / 2')
	else:
		W, Wf, Ws, S, H, A, G, n, P = (q[k] for k in ('W', 'Wf', 'Ws', 'S', 'H', 'A', 'G', 'n', 'P'))
	if min(W, Wf, Ws) < 0.15:
		e.append('trace narrower than 0.15 mm')
	if S - Ws / 2 - Wf / 2 < SHORT_GAP - 1e-9:
		e.append('short leg closer than %.3f mm to the feed leg (edge to edge)' % SHORT_GAP)
	if q['Nw'] > 0:                                    # Nw 0 = footprint without a notch (trace port, r4 and later)
		if S - Ws / 2 < q['Nw'] / 2 + MIN_GAP - 1e-9:
			e.append('short leg reaches into the feed notch')
		if q['Nw'] < Wf + 2 * 0.2 - 1e-9:
			e.append('notch narrower than the feed leg + 2 x 0.2 mm')
	if fm:
		pass
	elif n > 0:
		if A - W / 2 - Wf / 2 < MIN_GAP - 1e-9:
			e.append('finger 1 too close to the feed leg')
		if n > 1 and P - W < MIN_GAP - 1e-9:
			e.append('finger pitch leaves less than the minimum gap')
		if G < MIN_GAP + 0.05:
			e.append('meander bottom closer than %.2f mm to the ground edge' % (MIN_GAP + 0.05))
		if (H - W) - (G + W) < MIN_GAP - 1e-9 and n > 1:
			e.append('bottom links too close to the top links (H - G too small)')
	else:
		if A < Wf / 2 + 1.0:
			e.append('arm ends before the feed leg')
	if H - W < 0.5:
		e.append('arm too low')
	k = p.get('keepout')
	if k:
		u0, _, u1, v1 = local_bbox(p)
		m = k.get('m', 0.3)
		if u0 < k['u0'] + m - 1e-9 or u1 > k['u0'] + k['w'] - m + 1e-9 or v1 > k['h'] - m + 1e-9:
			e.append('copper outside the keep-out (u %.2f..%.2f, v ..%.2f; allowed u %.2f..%.2f, v ..%.2f)' % (
				u0, u1, v1, k['u0'] + m, k['u0'] + k['w'] - m, k['h'] - m))
		if q['Nw'] / 2 > min(-k['u0'], k['u0'] + k['w']):
			e.append('notch outside the keep-out')
	if board is not None and board.get('outline'):
		s = site(p, board)
		if s['rot'] % 90:
			e.append('site rotation must be a multiple of 90 degrees')
		boxes = [place(b, s) for b in r if b[4] != 'short'] + [place((b[0], 0.0, b[2], b[3]), s) for b in r if b[4] == 'short']
		d, pt = edge_clearance(boxes, board['outline'][0])
		if d < EDGE_MARGIN - 1e-6:
			e.append('copper %.2f mm from the board edge at (%.2f, %.2f), minimum %.1f' % (d, pt[0], pt[1], EDGE_MARGIN))
	return sorted(set(e))


def fixed_lines(p, board):
	r, _ = rects(p, board)
	return sorted({b[0] for b in r} | {b[2] for b in r}), sorted({b[1] for b in r} | {b[3] for b in r})


def size(p):
	"""Antenna footprint (copper bounding box above the ground edge) in mm: width, height, area."""
	u0, _, u1, v1 = local_bbox(p)
	out = {'w': round(u1 - u0, 3), 'h': round(v1, 3), 'area': round((u1 - u0) * v1, 2)}
	if p.get('keepout'):
		out['keepout'] = [p['keepout']['w'], p['keepout']['h']]
	return out


def describe(p):
	q = params(p)
	sz = size(p)
	keys = ('S', 'H', 'A', 'D', 'R', 'W') if p.get('family') == 'fmifa' else ('S', 'H', 'A', 'G', 'n', 'P', 'W')
	return p.get('family', 'mifa') + ' ' + ' '.join('%s=%g' % (k, q[k]) for k in keys) + \
		'  (%.1f x %.1f mm, L %.1f mm)' % (sz['w'], sz['h'], length(p))

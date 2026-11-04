"""Antenna geometry for the C23 rev B board simulation (simulation coordinates, mm, see export_board.py).

An antenna is a list of rectangles (x0, y0, x1, y1) on F.Cu. They may overlap (the copper is their union).

Fixed by the board (2026-11-02):
    feed leg centre x = FEED_X (AE1 pad 1), ground edge y = GND_Y, board top edge y = TOP_Y
    feed notch in the ground: x NOTCH_X0..NOTCH_X1, y GND_Y - 1 .. GND_Y (the feed trace from the L2/L3 matching network enters here)

Families
    ifa   short leg left of the feed, straight arm to the right
          S  short-to-feed spacing, centre to centre     Ws short leg width
          Wf feed leg width                               H  ground edge to arm bottom
          Wa arm width                                    L  arm open end x
    fifa  folded IFA: arm to the right up to x = L, a vertical drop of width Wa at the end, then a second
          horizontal segment back to the left at height H2 (bottom edge) ending at x = L - L2.
          L2 = Wa gives a plain bent-down arm end (no return segment).
"""
import math

FEED_X = -5.9
GND_Y = 11.0
TOP_Y = 17.0
NOTCH_X0, NOTCH_X1 = -7.4, -4.4
NOTCH_Y0 = 10.0
# Board revisions of the ground edge. 'base' in the antenna params picks one (default b1, which keeps old hashes).
#   b1  ground edge at KiCad y 89, notch bottom 90 (2026-11-02 layout, with the antenna-side shunt pads, then called L4)
#   b2  ground edge at KiCad y 90.4, notch bottom 90.22 (2026-11-03: antenna-side shunt removed, via fence 1.4 mm lower,
#       the ref L4 is now the 10 uH DC-DC inductor)
#   b2t5, b2t10  b2 made 5 / 10 mm taller below the RF area (stretch_board.py --dy), same antenna area
#   b2w4, b2w8   b2 made 4 / 8 mm wider to the right (stretch_board.py --dx), right corner centre moves
#   b2w8t10      b2w8 also made 10 mm taller
BASES = {'b1': {'GND_Y': 11.0, 'NOTCH_Y0': 10.0}, 'b2': {'GND_Y': 9.6, 'NOTCH_Y0': 8.78},
	'b2t5': {'GND_Y': 9.6, 'NOTCH_Y0': 8.78}, 'b2t10': {'GND_Y': 9.6, 'NOTCH_Y0': 8.78},
	'b2w4': {'GND_Y': 9.6, 'NOTCH_Y0': 8.78, 'CORNERS': [(-7.0, 7.0), (11.0, 7.0)]},
	'b2w8': {'GND_Y': 9.6, 'NOTCH_Y0': 8.78, 'CORNERS': [(-7.0, 7.0), (15.0, 7.0)]},
	'b2w8t10': {'GND_Y': 9.6, 'NOTCH_Y0': 8.78, 'CORNERS': [(-7.0, 7.0), (15.0, 7.0)]}}


def base(p):
	return BASES[p.get('base', 'b1')]
EDGE_MARGIN = 0.4          # copper to board edge
MIN_GAP = 0.3              # copper to copper inside the antenna
FEED_MAX_W = 1.5           # the trace channel at the notch bottom is about 1.9 mm wide (sim x -6.96..-5.05), a wider
                           # feed leg touches the ground there (2026-11-03: Wf 2 gave S11 0 dB)
CORNERS = [(-7.0, 7.0), (7.0, 7.0)]   # R10 corner centres near the antenna (x = 133+10, 167-10 in KiCad)
CORNER_R = 10.0

DEFAULTS = {
	'ifa': {'S': 3.5, 'Ws': 2.0, 'Wf': 1.0, 'H': 3.0, 'Wa': 1.0, 'L': 9.2},
	'fifa': {'S': 3.5, 'Ws': 1.0, 'Wf': 1.0, 'H': 4.0, 'Wa': 0.8, 'L': 6.0, 'H2': 1.8, 'L2': 4.0},
}


def placed_r011():
	"""The AE1 footprint as placed on the board (r011 dimensions)."""
	return {'family': 'ifa', 'S': 3.5, 'Ws': 2.0, 'Wf': 1.0, 'H': 3.0, 'Wa': 1.0, 'L': 9.1}


def rects(p):
	f = p['family']
	q = dict(DEFAULTS[f])
	q.update({k: v for k, v in p.items() if k not in ('family', 'base')})
	GND_Y, NOTCH_Y0 = base(p)['GND_Y'], base(p)['NOTCH_Y0']
	xf0, xf1 = FEED_X - q['Wf'] / 2, FEED_X + q['Wf'] / 2
	xs = FEED_X - q['S']
	xs0, xs1 = xs - q['Ws'] / 2, xs + q['Ws'] / 2
	ya0 = GND_Y + q['H']
	ya1 = ya0 + q['Wa']
	r = [
		(xs0, GND_Y - 0.25, xs1, ya1),          # short leg, overlaps the ground pour by 0.25 mm
		(xf0, NOTCH_Y0, xf1, ya0 + 1e-9),       # feed leg from the notch bottom (pad 1)
		(xs0, ya0, q['L'], ya1),                # arm
	]
	if f == 'fifa':
		yb0 = GND_Y + q['H2']
		yb1 = yb0 + q['Wa']
		r.append((q['L'] - q['Wa'], yb0, q['L'], ya1))        # drop
		r.append((q['L'] - q['L2'], yb0, q['L'], yb1))        # return segment
	return [tuple(round(v, 4) for v in b) for b in r], q


def check(p):
	r, q = rects(p)
	GND_Y = base(p)['GND_Y']
	errs = []
	xs1 = r[0][2]
	xf0, xf1 = r[1][0], r[1][2]
	if xf0 - xs1 < MIN_GAP - 1e-9:
		errs.append('short leg too close to the feed leg')
	if xs1 > NOTCH_X0 + 1e-9:
		errs.append('short leg reaches into the feed notch')
	if q['Wf'] > FEED_MAX_W + 1e-9:
		errs.append('feed leg wider than the trace channel at the notch bottom')
	if q['L'] < xf1 + 1.0:
		errs.append('arm ends before the feed leg')
	for (x0, y0, x1, y1) in r:
		for (x, y) in ((x0, y1), (x1, y1), (x0, y0), (x1, y0)):
			if y < GND_Y - 1.01:
				continue
			if y > TOP_Y - EDGE_MARGIN + 1e-9:
				errs.append('copper above the board edge margin')
			for cx, cy in base(p).get('CORNERS', CORNERS):
				if (x - cx) * (cx > 0) > 0 or (cx - x) * (cx < 0) > 0:
					if y > cy and math.hypot(x - cx, y - cy) > CORNER_R - EDGE_MARGIN + 1e-9:
						errs.append('copper outside the rounded corner (%.2f, %.2f)' % (x, y))
	if p['family'] == 'fifa':
		yb0, yb1 = GND_Y + q['H2'], GND_Y + q['H2'] + q['Wa']
		if q['H2'] < 1.0:
			errs.append('return segment closer than 1 mm to the ground edge')
		if q['H'] - (q['H2'] + q['Wa']) < 0.5 - 1e-9:
			errs.append('return segment closer than 0.5 mm to the arm')
		if q['L'] - q['L2'] < xf1 + 1.0:
			errs.append('return segment reaches the feed leg')
		if q['L2'] < q['Wa'] - 1e-9:
			errs.append('return segment shorter than the arm width')
	return sorted(set(errs))


def fixed_lines(p):
	r, _ = rects(p)
	xs = sorted({b[0] for b in r} | {b[2] for b in r})
	ys = sorted({b[1] for b in r} | {b[3] for b in r})
	return xs, ys


def describe(p):
	_, q = rects(p)
	b = '' if p.get('base', 'b1') == 'b1' else p['base'] + ' '
	return b + p['family'] + ' ' + ' '.join('%s=%g' % (k, q[k]) for k in DEFAULTS[p['family']])

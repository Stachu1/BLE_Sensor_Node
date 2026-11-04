"""Generate the printed IFA footprint BSN-C23.pretty/IFA_2G4.kicad_mod from the rev B board sims.

Usage: python gen_ifa_footprint.py
       python gen_ifa_footprint.py --sim '{"S": 3.5, "Ws": 2, "Wf": 1, "H": 5.0, "Wa": 1, "L": 9.0}'
Without --sim the final rev B geometry (FINAL below, hardware/C23/testing/RF/sim/results/RECOMMENDATION.md) is used.
--sim takes antenna.py "ifa" parameters of the rev B board sims (hardware/C23/testing/RF/sim, ground edge base
b2), for trying other geometries. The output is always IFA_2G4.kicad_mod.

Geometry (mm), as in ifa_param.py:
    x0  short leg left edge, from the board edge     Ws  short leg width
    S   short-to-feed leg spacing, centre to centre  Wf  feed leg width
    H   ground edge to arm bottom edge               Wa  arm width
    L   arm end (x of the open end, from the board edge)

Footprint origin: feed leg centre on the ground edge. The antenna points to -y, the ground is at +y.
Pad 1 is the feed (in the 1 mm ground notch, like the simulation port), pad 2 is the short to ground.
Both are joined by the antenna copper, so the footprint is a net tie (pads 1 and 2).
The antenna copper and the pads stay under solder mask (no F.Mask opening). The board finish is OSP, which
does not protect bare copper after reflow, so an exposed antenna would oxidise. The final sims include a 20 um
mask layer. Tune the antenna with L2 and L3 on the bench.
The keep-out covers the clearance on every copper layer: CLEARANCE above the ground edge, across the
board width BOARD_W, with the antenna x0 from the left board edge, as in the simulation.
"""
import json
import os
import sys

FINAL = {'S': 3.5, 'Ws': 2.0, 'Wf': 1.0, 'H': 5.0, 'Wa': 1.0, 'L': 9.0}   # rev B final, sims 2026-11-04
BOARD_W = 34.0      # board width the keep-out spans
CLEARANCE = 7.225   # footprint origin to the top board edge (set from B2 in main)
NOTCH_H = 1.0       # feed notch depth into the ground (simulation port gap)
NOTCH_SIDE = 1.0    # notch clearance on each side of the feed leg
OVERLAP = 0.25      # pads reach this far into the antenna legs so the copper joins

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'BSN-C23.pretty', 'IFA_2G4.kicad_mod')


def f(v):
	return f'{v:.4f}'.rstrip('0').rstrip('.')


def pts(points):
	return ' '.join(f'(xy {f(x)} {f(y)})' for x, y in points)


# rev B b2 layout (KiCad mm): left board edge, top board edge, footprint origin (AE1 position, feed leg centre),
# real ground edge (via fence and pours). The sim measures H from the real ground edge, the footprint from the origin.
B2 = {'board_left': 133.0, 'board_top': 83.0, 'origin_x': 144.1, 'origin_y': 90.225, 'gnd_y': 90.4}


def from_sim(q):
	"""antenna.py ifa parameters (sim, b2) -> generator parameters and the keep-out clearance."""
	b = B2
	p = {'x0': round(b['origin_x'] - q['S'] - q['Ws'] / 2 - b['board_left'], 4), 'Ws': q['Ws'], 'S': q['S'], 'Wf': q['Wf'],
		'H': round(q['H'] - (b['gnd_y'] - b['origin_y']), 4), 'Wa': q['Wa'], 'L': round(q['L'] + 150.0 - b['board_left'], 4)}
	return p, round(b['origin_y'] - b['board_top'], 4)


def main():
	global CLEARANCE
	args = sys.argv[1:]
	q = json.loads(args[args.index('--sim') + 1]) if '--sim' in args else dict(FINAL)
	p, CLEARANCE = from_sim(q)
	src = 'rev B sim (b2 layout) ' + json.dumps(q)
	xf = p['x0'] + p['Ws'] / 2 + p['S']          # feed leg centre, from the board edge
	sx0, sx1 = p['x0'] - xf, p['x0'] + p['Ws'] - xf
	fx0, fx1 = -p['Wf'] / 2, p['Wf'] / 2
	ya0, ya1 = -p['H'], -(p['H'] + p['Wa'])       # arm bottom and top edge
	xe = p['L'] - xf                              # open end
	left, right = -xf, BOARD_W - xf               # board edges
	n0, n1 = max(sx1, fx0 - NOTCH_SIDE), fx1 + NOTCH_SIDE

	antenna = [(sx0, 0), (sx0, ya1), (xe, ya1), (xe, ya0), (fx1, ya0), (fx1, 0),
	           (fx0, 0), (fx0, ya0), (sx1, ya0), (sx1, 0)]
	keepout = [(left, 0), (left, -CLEARANCE), (right, -CLEARANCE), (right, 0),
	           (n1, 0), (n1, NOTCH_H), (n0, NOTCH_H), (n0, 0)]
	board_note = 'Simulated on the C23 rev B board (34 x 34 mm, R10 corners, CR2032). '
	descr = (f'Printed inverted-F antenna, 2.4 GHz, openEMS {src}: '.replace('"', "'")
	         + ', '.join(f'{k} {f(v)}' for k, v in p.items())
	         + ' mm. ' + board_note +
	         f'Keep-out: {f(CLEARANCE)} mm above the ground edge on every copper layer, {f(BOARD_W)} mm wide, '
	         f'antenna short leg {f(p["x0"])} mm from the left board edge. Antenna under solder mask. Pad 1 feed, pad 2 ground.')

	crt = [(left, -CLEARANCE), (right, NOTCH_H + 0.25)]
	fpname = os.path.splitext(os.path.basename(OUT))[0]
	out = f'''(footprint "{fpname}"
	(version 20260206)
	(generator "pcbnew")
	(generator_version "10.0")
	(layer "F.Cu")
	(descr "{descr}")
	(tags "PCB antenna IFA inverted-F 2.4GHz BLE")
	(property "Reference" "REF**"
		(at {f(xe / 2)} {f(ya1 - 1.2)} 0)
		(layer "F.SilkS")
		(hide yes)
		(effects (font (size 1 1) (thickness 0.15)))
	)
	(property "Value" "{fpname}"
		(at {f(xe / 2)} {f(NOTCH_H + 1.2)} 0)
		(layer "F.Fab")
		(effects (font (size 1 1) (thickness 0.15)))
	)
	(property "Datasheet" ""
		(at 0 0 0)
		(layer "F.Fab")
		(hide yes)
		(effects (font (size 1 1) (thickness 0.15)))
	)
	(property "Description" "Printed IFA, 2.4 GHz"
		(at 0 0 0)
		(layer "F.Fab")
		(hide yes)
		(effects (font (size 1 1) (thickness 0.15)))
	)
	(attr exclude_from_pos_files exclude_from_bom)
	(net_tie_pad_groups "1,2")
	(duplicate_pad_numbers_are_jumpers no)
	(fp_poly
		(pts {pts(antenna)})
		(stroke (width 0) (type solid))
		(fill yes)
		(layer "F.Cu")
	)
	(fp_poly
		(pts {pts(keepout)})
		(stroke (width 0.1) (type solid))
		(fill no)
		(layer "Dwgs.User")
	)
	(fp_rect
		(start {f(crt[0][0])} {f(crt[0][1])})
		(end {f(crt[1][0])} {f(crt[1][1])})
		(stroke (width 0.05) (type solid))
		(fill no)
		(layer "F.CrtYd")
	)
	(fp_text user "${{REFERENCE}}"
		(at {f(xe / 2)} {f(ya1 - 1.2)} 0)
		(layer "F.Fab")
		(effects (font (size 1 1) (thickness 0.15)))
	)
	(fp_text user "antenna keep-out, all copper layers"
		(at {f((left + right) / 2)} {f(-CLEARANCE + 1)} 0)
		(layer "Dwgs.User")
		(effects (font (size 0.6 0.6) (thickness 0.1)))
	)
	(pad "1" connect rect
		(at 0 {f((NOTCH_H - OVERLAP) / 2)})
		(size {f(p['Wf'])} {f(NOTCH_H + OVERLAP)})
		(layers "F.Cu")
	)
	(pad "2" connect rect
		(at {f((sx0 + sx1) / 2)} {f((NOTCH_H - OVERLAP) / 2)})
		(size {f(p['Ws'])} {f(NOTCH_H + OVERLAP)})
		(layers "F.Cu")
		(zone_connect 2)
	)
	(zone
		(layers "*.Cu")
		(name "IFA keep-out")
		(hatch full 0.5)
		(connect_pads (clearance 0))
		(min_thickness 0.25)
		(keepout
			(tracks not_allowed)
			(vias not_allowed)
			(pads allowed)
			(copperpour not_allowed)
			(footprints not_allowed)
		)
		(placement (enabled no) (sheetname ""))
		(fill (thermal_gap 0.5) (thermal_bridge_width 0.5) (island_removal_mode 0))
		(polygon
			(pts {pts([(left, 0), (left, -CLEARANCE), (right, -CLEARANCE), (right, 0)])})
		)
	)
	(zone
		(layers "*.Cu")
		(name "IFA feed notch")
		(hatch full 0.5)
		(connect_pads (clearance 0))
		(min_thickness 0.25)
		(keepout
			(tracks allowed)
			(vias not_allowed)
			(pads allowed)
			(copperpour not_allowed)
			(footprints allowed)
		)
		(placement (enabled no) (sheetname ""))
		(fill (thermal_gap 0.5) (thermal_bridge_width 0.5) (island_removal_mode 0))
		(polygon
			(pts {pts([(n0, 0), (n1, 0), (n1, NOTCH_H), (n0, NOTCH_H)])})
		)
	)
	(embedded_fonts no)
)
'''
	open(OUT, 'w', encoding='utf-8', newline='\n').write(out)
	print('wrote', OUT, 'from', src)


if __name__ == '__main__':
	main()

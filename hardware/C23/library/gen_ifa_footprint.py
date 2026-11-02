"""Generate the printed IFA footprint (BSN-C23.pretty/IFA_2G4.kicad_mod) from the openEMS optimizer geometry.

Usage: python gen_ifa_footprint.py [best.json]
best.json is the optimizer's result file (ifa_optimizer/results/best.json). Without it the r011 geometry is used.

Geometry (mm), as in ifa_param.py:
    x0  short leg left edge, from the board edge     Ws  short leg width
    S   short-to-feed leg spacing, centre to centre  Wf  feed leg width
    H   ground edge to arm bottom edge               Wa  arm width
    L   arm end (x of the open end, from the board edge)

Footprint origin: feed leg centre on the ground edge. The antenna points to -y, the ground is at +y.
Pad 1 is the feed (in the 1 mm ground notch, like the simulation port), pad 2 is the short to ground.
Both are joined by the antenna copper, so the footprint is a net tie (pads 1 and 2).
The antenna copper and the pads stay under solder mask (no F.Mask opening). The board finish is OSP, which
does not protect bare copper after reflow, so an exposed antenna would oxidise. The simulation has no mask
layer, so the mask pulls the real resonance slightly lower. Tune it with the matching network on the bench.
The keep-out covers the clearance on every copper layer: CLEARANCE above the ground edge, across the
board width BOARD_W, with the antenna x0 from the left board edge, as in the simulation.
"""
import json
import os
import sys

R011 = {'x0': 4.0, 'Ws': 2.0, 'S': 3.5, 'Wf': 1.0, 'H': 3.0, 'Wa': 1.0, 'L': 23.5}
SOURCE = 'r011'
BOARD_W = 34.0      # board width the keep-out spans
CLEARANCE = 8.0     # ground edge to board edge (simulation: 41 - 33)
NOTCH_H = 1.0       # feed notch depth into the ground (simulation port gap)
NOTCH_SIDE = 1.0    # notch clearance on each side of the feed leg
OVERLAP = 0.25      # pads reach this far into the antenna legs so the copper joins

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'BSN-C23.pretty', 'IFA_2G4.kicad_mod')


def f(v):
	return f'{v:.4f}'.rstrip('0').rstrip('.')


def pts(points):
	return ' '.join(f'(xy {f(x)} {f(y)})' for x, y in points)


def main():
	p, src = dict(R011), SOURCE
	if len(sys.argv) > 1:
		best = json.load(open(sys.argv[1]))
		p, src = best['params'], best.get('id', os.path.basename(sys.argv[1]))
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
	descr = (f'Printed inverted-F antenna, 2.4 GHz, openEMS optimizer run {src}: '
	         + ', '.join(f'{k} {f(v)}' for k, v in p.items())
	         + f' mm. Simulated on a 40 x 41 mm board with a 40 x 33 mm ground, so re-check on the real outline. '
	         f'Keep-out: {f(CLEARANCE)} mm above the ground edge on every copper layer, {f(BOARD_W)} mm wide, '
	         f'antenna short leg {f(p["x0"])} mm from the left board edge. Antenna under solder mask. Pad 1 feed, pad 2 ground.')

	crt = [(left, -CLEARANCE), (right, NOTCH_H + 0.25)]
	out = f'''(footprint "IFA_2G4"
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
	(property "Value" "IFA_2G4"
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

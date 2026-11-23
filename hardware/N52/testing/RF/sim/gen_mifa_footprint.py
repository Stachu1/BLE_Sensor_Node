"""Write a KiCad footprint for a simulated MIFA into library/BSN-N52.pretty.

Usage:  python gen_mifa_footprint.py --generic               the generic BSN-N52 footprint: antenna.GENERIC_KEEPOUT
                                                             (12 x 5 mm) with the untuned start copper antenna.GENERIC
        python gen_mifa_footprint.py --run <hash>            a simulated antenna (results/runs/<hash>/case.json)
        python gen_mifa_footprint.py '<antenna json>' [--clear-w W] [--clear-h H]
        common options: --name MIFA_2G4 (footprint name), --out <dir.pretty>
The antenna json is the "antenna" dict of a case (antenna.py parameters, "site": {"mirror": true} for an arm
towards -x). The footprint is built from the same rectangles as the simulation (antenna.local_rects).

Footprint origin = feed leg centre on the ground edge, the same point as the simulation site, so after placing
AE1 on the board ./sim.sh export reads the site (position, rotation) from it. Antenna towards -y (KiCad), ground +y.
    pad 1  feed, fills the feed notch (v = -Nd .. +0.25), the feed trace arrives at the notch bottom. The simulation
           port spans the notch, so its reference plane is the notch bottom.
    pad 2  short to ground, reaches 1 mm into the ground pour.
    copper the antenna rectangles on F.Cu, under solder mask. Pads 1 and 2 are a net tie.
    keep-out  every copper layer: the antenna's fixed "keepout" box if it has one (the generic footprint and every
           antenna tuned inside it, so the board never changes when the copper is retuned), else the antenna bounding
           box + K, optionally widened to --clear-w x --clear-h. Plus the feed notch (tracks allowed). This is the
           same region sim_board.py cuts from the board copper.
A "Sim" property holds the parameters as JSON for export_board.py.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import antenna as ant  # noqa: E402

LIB = os.path.join(HERE, '..', '..', '..', 'library', 'BSN-N52.pretty')
if '--out' in sys.argv:
	LIB = sys.argv[sys.argv.index('--out') + 1]


def f(v):
	return f'{v:.4f}'.rstrip('0').rstrip('.') or '0'


def main():
	args = sys.argv[1:]
	name = args[args.index('--name') + 1] if '--name' in args else 'MIFA_2G4'
	src = 'untuned start geometry'
	if '--generic' in args:
		a = dict(ant.GENERIC)
	elif '--run' in args:
		h = args[args.index('--run') + 1]
		a = json.load(open(os.path.join(HERE, 'results', 'runs', h, 'case.json')))['antenna']
		src = 'tuned, sim run ' + h
	else:
		a = json.loads(args[0])
		src = 'from parameters'
	q = ant.params(a)
	mirror = bool(a.get('site', {}).get('mirror', False))
	sx = -1.0 if mirror else 1.0

	def kc(u, v):                                   # local (u, v) -> footprint (x, y), KiCad y down
		return sx * u, -v

	def rect_pts(u0, v0, u1, v1):
		(x0, y0), (x1, y1) = kc(u0, v0), kc(u1, v1)
		return [(min(x0, x1), min(y0, y1)), (max(x0, x1), min(y0, y1)), (max(x0, x1), max(y0, y1)), (min(x0, x1), max(y0, y1))]

	def pts(p):
		return ' '.join(f'(xy {f(x)} {f(y)})' for x, y in p)

	errs = ant.check(a)
	if errs:
		sys.exit('antenna breaks the geometry rules: ' + '; '.join(errs))
	rects, _ = ant.local_rects(a)
	u0, _, u1, v1 = ant.local_bbox(a)
	K = q['K']
	cu0, cu1, ch = u0 - K, u1 + K, v1 + K
	k = a.get('keepout')
	if k:
		cu0, cu1, ch = k['u0'], k['u0'] + k['w'], k['h']
	elif '--clear-w' in args:
		w = float(args[args.index('--clear-w') + 1])
		c = (u0 + u1) / 2
		cu0, cu1 = min(cu0, c - w / 2), max(cu1, c + w / 2)
	if '--clear-h' in args and not k:
		ch = max(ch, float(args[args.index('--clear-h') + 1]))
	Nd, Nw, Wf, Ws, S = q['Nd'], q['Nw'], q['Wf'], q['Ws'], q['S']
	ov = ant.OVERLAP
	polys = '\n'.join(f'''	(fp_poly
		(pts {pts(rect_pts(*r[:4]))})
		(stroke (width 0) (type solid))
		(fill yes)
		(layer "F.Cu")
	)''' for r in rects if r[4] != 'short') + '\n' + f'''	(fp_poly
		(pts {pts(rect_pts(-S - Ws / 2, 0.0, -S + Ws / 2, q['H']))})
		(stroke (width 0) (type solid))
		(fill yes)
		(layer "F.Cu")
	)'''
	sim = json.dumps({'antenna': {k: v for k, v in a.items() if k != 'site'}, 'mirror': mirror}).replace('"', '\\"')
	sz = ant.size(a)
	kotxt = 'keep-out %s x %s mm' % (f(cu1 - cu0), f(ch))
	descr = ('Printed meandered inverted-F antenna (MIFA), 2.4 GHz, BSN-N52 openEMS sims, %s: ' % src + ant.describe(a) +
		'. Origin = feed point on the ground edge, ' + kotxt + ' on every copper layer (fixed, the antenna is tuned inside it). '
		'Antenna under solder mask. Pad 1 feed (L-match at the notch bottom), pad 2 ground.')
	(px1, py1) = kc(0, (ov - Nd) / 2)
	(px2, py2) = kc(-S, (ov - 1.0) / 2)
	ko = rect_pts(cu0, 0.0, cu1, ch)
	notch = rect_pts(-Nw / 2, -Nd, Nw / 2, 0.0)
	lx, ly = kc((u0 + u1) / 2, ch + 0.8)
	out = f'''(footprint "{name}"
	(version 20260206)
	(generator "pcbnew")
	(generator_version "10.0")
	(layer "F.Cu")
	(descr "{descr}")
	(tags "PCB antenna MIFA meander inverted-F 2.4GHz BLE")
	(property "Reference" "AE1"
		(at {f(lx)} {f(ly)} 0)
		(layer "F.SilkS")
		(hide yes)
		(effects (font (size 0.8 0.8) (thickness 0.12)))
	)
	(property "Value" "{name}"
		(at {f(lx)} {f(Nd + 1.2)} 0)
		(layer "F.Fab")
		(effects (font (size 0.8 0.8) (thickness 0.12)))
	)
	(property "Datasheet" ""
		(at 0 0 0)
		(layer "F.Fab")
		(hide yes)
		(effects (font (size 1 1) (thickness 0.15)))
	)
	(property "Description" "Printed MIFA, 2.4 GHz, {f(sz['w'])} x {f(sz['h'])} mm"
		(at 0 0 0)
		(layer "F.Fab")
		(hide yes)
		(effects (font (size 1 1) (thickness 0.15)))
	)
	(property "Sim" "{sim}"
		(at 0 0 0)
		(layer "F.Fab")
		(hide yes)
		(effects (font (size 0.5 0.5) (thickness 0.08)))
	)
	(attr exclude_from_pos_files exclude_from_bom)
	(net_tie_pad_groups "1,2")
	(duplicate_pad_numbers_are_jumpers no)
{polys}
	(fp_rect
		(start {f(min(p[0] for p in ko))} {f(min(p[1] for p in ko))})
		(end {f(max(p[0] for p in ko))} {f(Nd + 0.25)})
		(stroke (width 0.05) (type solid))
		(fill no)
		(layer "F.CrtYd")
	)
	(fp_poly
		(pts {pts(ko)})
		(stroke (width 0.1) (type solid))
		(fill no)
		(layer "Dwgs.User")
	)
	(fp_text user "{kotxt}, all copper layers"
		(at {f(sx * (cu0 + cu1) / 2)} {f(-ch - 0.6)} 0)
		(layer "Dwgs.User")
		(effects (font (size 0.6 0.6) (thickness 0.1)))
	)
	(fp_text user "${{REFERENCE}}"
		(at {f(lx)} {f(ly)} 0)
		(layer "F.Fab")
		(effects (font (size 0.8 0.8) (thickness 0.12)))
	)
	(pad "1" connect rect
		(at {f(px1)} {f(py1)})
		(size {f(Wf)} {f(Nd + ov)})
		(layers "F.Cu")
	)
	(pad "2" connect rect
		(at {f(px2)} {f(py2)})
		(size {f(Ws)} {f(1.0 + ov)})
		(layers "F.Cu")
		(zone_connect 2)
	)
	(zone
		(layers "*.Cu")
		(name "MIFA keep-out")
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
			(pts {pts(ko)})
		)
	)
	(zone
		(layers "*.Cu")
		(name "MIFA feed notch")
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
			(pts {pts(notch)})
		)
	)
	(embedded_fonts no)
)
'''
	os.makedirs(LIB, exist_ok=True)
	p = os.path.join(LIB, name + '.kicad_mod')
	open(p, 'w', encoding='utf-8', newline='\n').write(out)
	print('wrote', os.path.abspath(p), '-', ant.describe(a))


if __name__ == '__main__':
	main()

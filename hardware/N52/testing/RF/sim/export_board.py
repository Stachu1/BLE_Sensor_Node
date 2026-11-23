"""Export BSN-N52.kicad_pcb to board.json for the openEMS sims (sim_board.py). Same format as synth_board.py.

Run with KiCad's python (pcbnew 10.0), or ./sim.sh export <rev>:
    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" export_board.py ../../../BSN-N52.kicad_pcb build/<rev>

The board file is only read. Zones are refilled in memory and never saved.

board.json (mm, simulation coordinates): x_sim = x_kicad - ORIGIN[0], y_sim = ORIGIN[1] - y_kicad, F.Cu at the top.
ORIGIN is the centre of the board outline (rounded to 0.1 mm) and is stored as origin_kicad.
    stackup  copper layers (z, B.Cu = 0) and dielectrics, from the board file. A board without a stack-up section
             gets FR4 (er 4.5, tan d 0.02) of the board thickness (2 layers) or the JLC 7628 stack (4 layers).
    outline  board outline polygon
    copper   per layer, hole-free polygons of all copper except the antenna AE1
    site     antenna feed point and rotation from the AE1 footprint (gen_mifa_footprint.py puts the origin on the
             feed point at the ground edge), and its "Sim" property (the MIFA parameters it was made from)
    vias, pads (BT1, AE1 and every part with a pad on the AE1 feed net, e.g. L1), battery (CR1632 if BT1 exists)
    feed     {"net": AE1 pad 1 net, "parts": refs of the other parts on it}: feedport.py puts the "trace" port on
             the feed trace next to the nearest of them (the end of the matching network)
"""
import json
import os
import re
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(HERE, '..', '..', '..', 'BSN-N52.kicad_pcb')
ANTENNA_REF = 'AE1'
PAD_REFS = ['AE1', 'BT1', 'L2', 'C1']   # L2 / C1: the rest of the T match (sim parts on their pads, r7 2026-11-15)
MAX_ERR = pcbnew.FromMM(0.01)
ORIGIN = [0.0, 0.0]


def to_sim(x, y):
	return (round(pcbnew.ToMM(x) - ORIGIN[0], 4), round(ORIGIN[1] - pcbnew.ToMM(y), 4))


def area(pts):
	return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))


def polyset_to_list(ps):
	ps.Simplify()
	ps.Fracture()
	out = []
	for i in range(ps.OutlineCount()):
		ol = ps.COutline(i)
		pts = [to_sim(ol.CPoint(k).x, ol.CPoint(k).y) for k in range(ol.PointCount())]
		if len(pts) >= 3 and abs(area(pts)) > 1e-4:
			out.append(pts)
	return out


def stackup(board, layers):
	txt = open(board.GetFileName(), encoding='utf-8').read()
	thick = float(re.search(r'\(general\s*\(thickness ([\d.]+)', txt).group(1))
	cu, diel = [], []
	if '(stackup' in txt:
		i = txt.index('(stackup')
		depth, j = 0, i
		while True:
			depth += txt[j] == '('
			depth -= txt[j] == ')'
			j += 1
			if depth == 0:
				break
		for m in re.finditer(r'\(layer "([^"]+)"(.*?)\n\t\t\t\)', txt[i:j], re.S):
			name, body = m.group(1), m.group(2)
			t = re.search(r'\(thickness ([\d.]+)', body)
			e = re.search(r'\(epsilon_r ([\d.]+)', body)
			d = re.search(r'\(loss_tangent ([\d.]+)', body)
			l = {'name': name, 't': float(t.group(1)) if t else 0.0, 'er': float(e.group(1)) if e else 4.5,
				'tand': float(d.group(1)) if d else 0.02}
			if name.endswith('.Cu'):
				cu.append(l)
			elif name.startswith('dielectric'):
				diel.append(l)
	if [l['name'] for l in cu] != layers or len(diel) != len(layers) - 1:
		print('no usable stack-up in the board file, using defaults for %d layers, %.3f mm' % (len(layers), thick))
		cu = [{'name': n, 't': 0.035} for n in layers]
		if len(layers) == 2:
			diel = [{'name': 'core', 't': thick, 'er': 4.5, 'tand': 0.02}]
		else:
			pp = 0.2104
			diel = [{'name': 'prepreg1', 't': pp, 'er': 4.4, 'tand': 0.02},
				{'name': 'core', 't': thick - 2 * pp, 'er': 4.5, 'tand': 0.02},
				{'name': 'prepreg2', 't': pp, 'er': 4.4, 'tand': 0.02}]
	# z from B.Cu = 0 upwards, copper as zero-thickness sheets
	z = {layers[-1]: 0.0}
	for k in range(len(layers) - 2, -1, -1):
		z[layers[k]] = z[layers[k + 1]] + diel[k]['t']
	return {'copper': {n: {'z': round(z[n], 5), 't': l['t']} for n, l in zip(layers, cu)},
		'dielectrics': [{'name': d['name'] + ('_%d' % k if len(diel) > 1 else ''), 'z0': round(z[layers[k + 1]], 5),
			'z1': round(z[layers[k]], 5), 'er': d['er'], 'tand': d['tand']} for k, d in enumerate(diel)]}


def main():
	path = sys.argv[1] if len(sys.argv) > 1 else BOARD
	out_dir = sys.argv[2] if len(sys.argv) > 2 else sys.exit('usage: export_board.py <board.kicad_pcb> <out_dir>')
	if os.path.exists(os.path.join(out_dir, 'board.json')):
		sys.exit(out_dir + '/board.json exists: export a changed board into a new folder (the result cache keys on the path)')
	os.makedirs(out_dir, exist_ok=True)
	board = pcbnew.LoadBoard(path)
	pcbnew.ZONE_FILLER(board).Fill(board.Zones())
	layers = [board.GetLayerName(l) for l in board.GetEnabledLayers().CuStack()]

	ol = pcbnew.SHAPE_POLY_SET()
	if not board.GetBoardPolygonOutlines(ol, False) or ol.OutlineCount() == 0:
		sys.exit('no closed board outline on Edge.Cuts')
	bb = ol.BBox()
	ORIGIN[0] = round(pcbnew.ToMM(bb.Centre().x), 1)
	ORIGIN[1] = round(pcbnew.ToMM(bb.Centre().y), 1)
	data = {'source': os.path.abspath(path).replace('\\', '/'), 'origin_kicad': list(ORIGIN), 'stackup': stackup(board, layers)}
	data['outline'] = polyset_to_list(ol)

	copper = {}
	for name in layers:
		lid = board.GetLayerID(name)
		ps = pcbnew.SHAPE_POLY_SET()
		for zn in board.Zones():
			if zn.GetIsRuleArea() or not zn.IsOnLayer(lid):
				continue
			ps.BooleanAdd(zn.GetFilledPolysList(lid))
		for t in board.GetTracks():
			if t.IsOnLayer(lid):
				t.TransformShapeToPolygon(ps, lid, 0, MAX_ERR, pcbnew.ERROR_INSIDE)
		for fp in board.GetFootprints():
			if fp.GetReference() == ANTENNA_REF:
				continue
			for p in fp.Pads():
				if p.IsOnLayer(lid):
					p.TransformShapeToPolygon(ps, lid, 0, MAX_ERR, pcbnew.ERROR_INSIDE)
			for g in fp.GraphicalItems():
				if g.GetLayer() == lid:
					g.TransformShapeToPolygon(ps, lid, 0, MAX_ERR, pcbnew.ERROR_INSIDE)
		for g in board.GetDrawings():
			if g.GetLayer() == lid and hasattr(g, 'TransformShapeToPolygon'):
				g.TransformShapeToPolygon(ps, lid, 0, MAX_ERR, pcbnew.ERROR_INSIDE)
		copper[name] = polyset_to_list(ps)
		print(f'{name}: {len(copper[name])} polygons, {sum(len(p) for p in copper[name])} vertices')
	data['copper'] = copper

	ae = board.FindFootprintByReference(ANTENNA_REF)
	if ae is not None:
		if ae.IsFlipped():
			sys.exit('AE1 is on the back side, the sims put the antenna on F.Cu')
		rot = int(round(ae.GetOrientationDegrees())) % 360
		if rot % 90:
			sys.exit('AE1 rotation %d: only multiples of 90 degrees are supported' % rot)
		sim_par = {}
		if ae.HasField('Sim'):
			sim_par = json.loads(ae.GetFieldText('Sim'))
		x, y = to_sim(*ae.GetPosition())
		data['site'] = {'x': x, 'y': y, 'rot': rot, 'mirror': bool(sim_par.get('mirror', False))}
		ps = pcbnew.SHAPE_POLY_SET()
		lid = board.GetLayerID('F.Cu')
		for p in ae.Pads():
			p.TransformShapeToPolygon(ps, lid, 0, MAX_ERR, pcbnew.ERROR_INSIDE)
		for g in ae.GraphicalItems():
			if g.GetLayer() == lid:
				g.TransformShapeToPolygon(ps, lid, 0, MAX_ERR, pcbnew.ERROR_INSIDE)
		data['ae1'] = {'params': sim_par.get('antenna'), 'pos': [x, y], 'rot': rot, 'copper': polyset_to_list(ps)}
		print('antenna site from AE1:', data['site'], 'params', sim_par.get('antenna'))
	else:
		data['site'] = None
		data['ae1'] = None
		print('no AE1 footprint: cases must give the antenna site')

	vias = []
	lid = board.GetLayerID('F.Cu')
	for t in board.GetTracks():
		if t.GetClass() == 'PCB_VIA':
			x, y = to_sim(t.GetPosition().x, t.GetPosition().y)
			vias.append({'x': x, 'y': y, 'drill': pcbnew.ToMM(t.GetDrillValue()), 'd': pcbnew.ToMM(t.GetWidth(lid)),
				'net': t.GetNetname()})
	data['vias'] = vias
	print(f'vias: {len(vias)}')

	feed = {'net': None, 'parts': []}
	if ae is not None:
		p1 = [p for p in ae.Pads() if p.GetNumber() == '1']
		if p1:
			feed['net'] = p1[0].GetNetname()
			for fp in board.GetFootprints():
				if fp.GetReference() != ANTENNA_REF and any(p.GetNetname() == feed['net'] for p in fp.Pads()):
					feed['parts'].append(fp.GetReference())
	data['feed'] = feed
	print('feed net', feed)
	pads = {}
	for ref in PAD_REFS + [r for r in feed['parts'] if r not in PAD_REFS]:
		fp = board.FindFootprintByReference(ref)
		if fp is None:
			print('no footprint', ref)
			continue
		lst = []
		for p in fp.Pads():
			bbx = p.GetBoundingBox()
			x0, y0 = to_sim(bbx.GetLeft(), bbx.GetBottom())
			x1, y1 = to_sim(bbx.GetRight(), bbx.GetTop())
			lst.append({'num': p.GetNumber(), 'net': p.GetNetname(), 'c': list(to_sim(p.GetPosition().x, p.GetPosition().y)),
				'bbox': [x0, y0, x1, y1], 'layers': [n for n in layers if p.IsOnLayer(board.GetLayerID(n))]})
		pads[ref] = {'pos': list(to_sim(*fp.GetPosition())), 'rot': fp.GetOrientationDegrees(),
			'side': 'B' if fp.IsFlipped() else 'F', 'pads': lst}
	data['pads'] = pads
	data['battery'] = {'d': 16.0, 't': 3.2, 'gap': 0.2} if 'BT1' in pads else None

	out = os.path.join(out_dir, 'board.json')
	with open(out, 'w') as fh:
		json.dump(data, fh)
	print('wrote', out, 'origin (KiCad)', ORIGIN)


if __name__ == '__main__':
	main()

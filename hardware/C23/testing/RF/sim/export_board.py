"""Export BSN-C23.kicad_pcb to board.json for the openEMS board simulation (sim_board.py).

Run with KiCad's python (pcbnew 10.0):
    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" export_board.py [board.kicad_pcb] [out_dir]

The board file is only read. Zones are refilled in memory and never saved.

board.json (all lengths in mm, simulation coordinates):
    x_sim = x_kicad - ORIGIN[0],  y_sim = ORIGIN[1] - y_kicad   (y flipped so F.Cu faces +z)
    stackup  copper layers with z (F.Cu on top) and the dielectrics between them
    outline  board outline polygon
    copper   per layer, hole-free polygons (KiCad Fracture) of all copper except the antenna AE1
    ae1      the antenna copper as placed (F.Cu polygon + pads), for the "as placed" case
    vias     x, y, drill, outer diameter, net
    pads     pads of the RF parts, the battery holder and U1 ANT (centre, size, net)
Also writes one PNG preview per copper layer (matplotlib, optional).
"""
import json
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
BOARD = os.path.join(REPO, 'hardware', 'C23', 'BSN-C23.kicad_pcb')
ORIGIN = (150.0, 100.0)                 # board centre in KiCad coordinates
LAYERS = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
ANTENNA_REF = 'AE1'
# L4 is not exported: the antenna-side shunt L4 was removed (b2 layout) and after re-annotation the reference L4
# is the 10 uH DC-DC inductor, which is not part of the RF window.
PAD_REFS = ['AE1', 'J2', 'L2', 'L3', 'C7', 'C8', 'C9', 'L1', 'U1', 'BT1']
MAX_ERR = pcbnew.FromMM(0.01)


def to_sim(x, y):
	return (round(pcbnew.ToMM(x) - ORIGIN[0], 4), round(ORIGIN[1] - pcbnew.ToMM(y), 4))


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


def area(pts):
	return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))


def stackup(board):
	"""Read the stack-up from the board file text (the python stack-up API is not exposed in 10.0)."""
	txt = open(board.GetFileName(), encoding='utf-8').read()
	i = txt.index('(stackup')
	layers, depth, j = [], 0, i
	while True:
		c = txt[j]
		depth += c == '('
		depth -= c == ')'
		j += 1
		if depth == 0:
			break
	block = txt[i:j]
	import re
	for m in re.finditer(r'\(layer "([^"]+)"(.*?)\n\t\t\t\)', block, re.S):
		name, body = m.group(1), m.group(2)
		t = re.search(r'\(thickness ([\d.]+)', body)
		e = re.search(r'\(epsilon_r ([\d.]+)', body)
		d = re.search(r'\(loss_tangent ([\d.]+)', body)
		layers.append({'name': name, 't': float(t.group(1)) if t else 0.0,
			'er': float(e.group(1)) if e else None, 'tand': float(d.group(1)) if d else None})
	# z from B.Cu = 0 upwards, copper as zero-thickness sheets at the copper's dielectric-side face
	cu = [l for l in layers if l['name'].endswith('.Cu')]
	diel = [l for l in layers if l['name'].startswith('dielectric')]
	assert [l['name'] for l in cu] == LAYERS and len(diel) == 3, (cu, diel)
	z = {'B.Cu': 0.0}
	z['In2.Cu'] = diel[2]['t']
	z['In1.Cu'] = z['In2.Cu'] + diel[1]['t']
	z['F.Cu'] = z['In1.Cu'] + diel[0]['t']
	dz = [(z['In1.Cu'], z['F.Cu'], diel[0]), (z['In2.Cu'], z['In1.Cu'], diel[1]), (0.0, z['In2.Cu'], diel[2])]
	return {
		'copper': {n: {'z': round(z[n], 5), 't': l['t']} for n, l in zip(LAYERS, cu)},
		'dielectrics': [{'name': d['name'], 'z0': round(a, 5), 'z1': round(b, 5), 'er': d['er'], 'tand': d['tand']}
			for a, b, d in dz],
	}


def main():
	path = sys.argv[1] if len(sys.argv) > 1 else BOARD
	out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'build')
	os.makedirs(out_dir, exist_ok=True)
	board = pcbnew.LoadBoard(path)
	pcbnew.ZONE_FILLER(board).Fill(board.Zones())

	data = {'source': os.path.relpath(path, REPO).replace('\\', '/'), 'origin_kicad': ORIGIN,
		'stackup': stackup(board)}

	# outline
	ol = pcbnew.SHAPE_POLY_SET()
	board.GetBoardPolygonOutlines(ol, False)
	data['outline'] = polyset_to_list(ol)

	copper = {}
	for name in LAYERS:
		lid = board.GetLayerID(name)
		ps = pcbnew.SHAPE_POLY_SET()
		for z in board.Zones():
			if z.GetIsRuleArea() or not z.IsOnLayer(lid):
				continue
			ps.BooleanAdd(z.GetFilledPolysList(lid))
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

	# antenna as placed
	ae = board.FindFootprintByReference(ANTENNA_REF)
	ps = pcbnew.SHAPE_POLY_SET()
	lid = board.GetLayerID('F.Cu')
	for p in ae.Pads():
		p.TransformShapeToPolygon(ps, lid, 0, MAX_ERR, pcbnew.ERROR_INSIDE)
	for g in ae.GraphicalItems():
		if g.GetLayer() == lid:
			g.TransformShapeToPolygon(ps, lid, 0, MAX_ERR, pcbnew.ERROR_INSIDE)
	data['ae1'] = {'pos': to_sim(*ae.GetPosition()), 'copper': polyset_to_list(ps)}

	vias = []
	for t in board.GetTracks():
		if t.GetClass() == 'PCB_VIA':
			x, y = to_sim(t.GetPosition().x, t.GetPosition().y)
			vias.append({'x': x, 'y': y, 'drill': pcbnew.ToMM(t.GetDrillValue()),
				'd': pcbnew.ToMM(t.GetWidth(lid)), 'net': t.GetNetname()})
	data['vias'] = vias
	print(f'vias: {len(vias)}')

	pads = {}
	for ref in PAD_REFS:
		fp = board.FindFootprintByReference(ref)
		if fp is None:
			print('no footprint', ref)
			continue
		lst = []
		for p in fp.Pads():
			if ref == 'U1' and 'ANT' not in p.GetNetname():
				continue
			bb = p.GetBoundingBox()
			x0, y0 = to_sim(bb.GetLeft(), bb.GetBottom())
			x1, y1 = to_sim(bb.GetRight(), bb.GetTop())
			cx, cy = to_sim(p.GetPosition().x, p.GetPosition().y)
			lst.append({'num': p.GetNumber(), 'net': p.GetNetname(), 'c': [cx, cy], 'bbox': [x0, y0, x1, y1],
				'layers': [n for n in LAYERS if p.IsOnLayer(board.GetLayerID(n))]})
		pads[ref] = {'pos': to_sim(*fp.GetPosition()), 'rot': fp.GetOrientationDegrees(),
			'side': 'B' if fp.IsFlipped() else 'F', 'pads': lst}
	data['pads'] = pads

	out = os.path.join(out_dir, 'board.json')
	with open(out, 'w') as fh:
		json.dump(data, fh)
	print('wrote', out)

	try:
		import matplotlib
		matplotlib.use('Agg')
		import matplotlib.pyplot as plt
		from matplotlib.patches import Polygon
		for name in LAYERS:
			fig, ax = plt.subplots(figsize=(8, 8))
			for o in data['outline']:
				ax.add_patch(Polygon(o, fill=False, ec='k'))
			for pts in copper[name]:
				ax.add_patch(Polygon(pts, fc='#c87533', ec='none', alpha=0.8))
			if name == 'F.Cu':
				for pts in data['ae1']['copper']:
					ax.add_patch(Polygon(pts, fc='#3060c0', ec='none', alpha=0.8))
			for v in vias:
				ax.add_patch(plt.Circle((v['x'], v['y']), v['d'] / 2, fc='k'))
			ax.set_xlim(-18, 18)
			ax.set_ylim(-18, 18)
			ax.set_aspect('equal')
			ax.set_title(name)
			fig.savefig(os.path.join(out_dir, f'preview_{name.replace(".", "_")}.png'), dpi=120)
			plt.close(fig)
	except ImportError:
		print('matplotlib not available, no previews')


if __name__ == '__main__':
	main()

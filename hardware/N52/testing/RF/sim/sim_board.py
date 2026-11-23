"""openEMS simulation of the BSN-N52 board (board.json from export_board.py or synth_board.py) with a MIFA.

Usage (server, openEMS venv):  python sim_board.py <run_dir> [threads] [--post]
<run_dir>/case.json:
    board      path to board.json (relative to this script's folder)
    antenna    {"family": "mifa", params..., "site": {...}} (antenna.py)
    ports      "feed"   one 50 ohm lumped port across the feed notch at the antenna site (the antenna feed point).
                        Only for boards WITHOUT a routed feed trace (synthetic boards, make_board_copy.py copies):
                        on r2 the notch port's lower end landed on the routed trace instead of the ground.
               "trace"  the routed feed trace drives the antenna: two 100 ohm sub-ports across the gaps between the
                        trace and the pour next to the end of the matching network (case key "trace_port", from
                        feedport.py, runner.py fills it in). No notch cut, no tab, the footprint feed pad is added.
    battery    true: CR1632 cell and holder clip as metal (needs BT1 pads in board.json)
    mask       "none" | "explicit" (20 um, er 3.8, both sides, resolved in z: much smaller timestep)
    er_scale, tand_scale   multiply the dielectric er / loss tangent (sensitivity, tand_scale 0 = lossless)
    nf2ff      true: radiation efficiency and pattern at NF2FF_F (own transform, farfield.py)
    mesh       overrides of MESH below
    keep_fields  keep the openEMS sim folder (dumps)
    port_at    {"ref": "L2", "net": "Net-(U2-ANT)", "len": 0.2}: the trace port beside that pad instead of the
               antenna-side pad of L1 (runner.py fills trace_port with it), so the matching network is in the model
    parts      {"L1": {"L": 5.1e-9, "Q": 50}, "C1": {"C": 1e-12, "Q": 100}, ...} real parts as lumped elements on
               their pads (gap between the two pads, on F.Cu): L = series R-L with R = wL/Q, C = C parallel R = Q/(wC).
               Unstable on the BSN fine mesh with mask (2026-11-04), watch the energy of a parts run.
    part_ports ["L2", "C1", "L1"]: 50 ohm lumped ports across those part gaps (no part fitted), ports.npz holds V and I
               of every port. One run per excitation, case key "excite" (0 = the trace port, k = part_ports[k-1]).
               The S-matrix of the network + antenna comes from all runs, the parts are added on the laptop
               (stable, unlike the lumped L / C elements: the smoke run r7 11afcc8780 grew after the pulse).
    field_dumps  "fd": only the 2.44 GHz phasors. true: field dumps for ParaView in <run_dir>/sim (kept, keep_fields implied), see add_dumps()
Writes <run_dir>/result.json, S11.csv and pattern.npz. The openEMS field data is deleted after use.

Board copper inside the antenna keep-out (antenna.clear_rects, bounding box + K and the feed notch) is removed on
every layer by thin dielectric boxes with a higher priority than the board copper, so any board can take any
antenna without a new export. The antenna copper has a higher priority again.
"""
import json
import os
import shutil
import sys
import time

import numpy as np
from CSXCAD import ContinuousStructure
from openEMS import openEMS
from openEMS.physical_constants import EPS0

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import antenna as ant  # noqa: E402
from farfield import farfield  # noqa: E402

F0, FC = 2.45e9, 1.2e9
F = np.linspace(1.6e9, 3.4e9, 1801)
NF2FF_F = [2.40e9, 2.44e9, 2.48e9]
BLE = (2.400e9, 2.4835e9)
MESH = {'ant': 0.2, 'port': 0.1, 'board': 0.6, 'max': 4.0, 'air': 30.0, 'grow': 1.3, 'diel': 0.2, 'cu_z': 0.07,
	'merge': 0.05, 'end': 1e-4}
MASK_T, MASK_ER = 0.02, 3.8
NF2FF_OS = 4
PML = 8
POST_ONLY = '--post' in sys.argv


def graded_lines(fixed, zones, lo, hi, maxc, grow, merge):
	"""Mesh lines through the fixed coordinates, cell size from the zones (z0, z1, size) growing by 'grow' outside
	them, capped at maxc. PML cells are added outside lo..hi."""
	def cell(q):
		return min([maxc] + [r + (grow - 1) * max(z0 - q, 0, q - z1) for z0, z1, r in zones])
	pts = np.unique(np.round(np.concatenate([np.asarray(fixed, float), [lo, hi]]), 6))
	pts = pts[(pts >= lo) & (pts <= hi)]
	keep = [pts[0]]
	for p in pts[1:]:
		if p - keep[-1] >= merge:
			keep.append(p)
	pts = np.array(keep)
	lines = [pts[0]]
	for a, b in zip(pts[:-1], pts[1:]):
		s = np.linspace(a, b, 4001)
		w = np.concatenate([[0], np.cumsum(np.diff(s) / np.array([cell(q) for q in (s[:-1] + s[1:]) / 2]))])
		n = max(int(np.ceil(w[-1] - 1e-9)), 1)
		lines += list(np.interp(np.linspace(0, w[-1], n + 1)[1:], w, s))
	lines = np.array(lines)
	d0, d1 = lines[1] - lines[0], lines[-1] - lines[-2]
	lines = np.concatenate([lines[0] - d0 * np.arange(PML, 0, -1), lines, lines[-1] + d1 * np.arange(1, PML + 1)])
	return np.round(lines, 6)


def battery_parts(board, st):
	"""CR1632 cell (one metal cylinder) and the holder: the - pad under the cell joined to the cell, the + clip
	as two vertical straps at the + pads and a strap across the far face of the cell. Returns boxes, cylinder,
	z extent and fixed lines."""
	bt = board['pads']['BT1']
	b = board['battery']
	side = bt['side']
	zs = st['copper']['F.Cu']['z'] if side == 'F' else 0.0
	sg = 1.0 if side == 'F' else -1.0
	z_near, z_far = zs + sg * b['gap'], zs + sg * (b['gap'] + b['t'])
	z_clip = z_far + sg * 0.2            # the clip strap is a 0.2 mm thick bar on the far (+) face of the cell.
	                                     # A zero-thickness strap on the cell face, or 0.2 mm off it, was dropped by
	                                     # openEMS ("Unused primitive", cause not found).
	negs = [p for p in bt['pads'] if p['num'] == '2']
	pos = [p for p in bt['pads'] if p['num'] == '1']
	(ax, ay), (bx, by) = pos[0]['c'], pos[1]['c']
	# cell centre = midpoint of the + clip pads (the - contact can be split into several pads, BSN-N52 r2 has 3).
	# On the older boards with one - pad under the cell centre this is the same point, so their runs are unchanged.
	cx, cy = (ax + bx) / 2, (ay + by) / 2
	boxes = [([p['c'][0] - 1.5, p['c'][1] - 1.5, zs], [p['c'][0] + 1.5, p['c'][1] + 1.5, z_near]) for p in negs]   # - contacts
	along_x = abs(bx - ax) > abs(by - ay)
	for p in pos:
		px, py = p['c']
		if along_x:
			boxes.append(([px, py - 1.5, zs], [px, py + 1.5, z_clip]))
		else:
			boxes.append(([px - 1.5, py, zs], [px + 1.5, py, z_clip]))
	if along_x:
		boxes.append(([min(ax, bx), ay - 1.5, z_far], [max(ax, bx), ay + 1.5, z_clip]))
	else:
		boxes.append(([ax - 1.5, min(ay, by), z_far], [ax + 1.5, max(ay, by), z_clip]))
	cyl = ([cx, cy, min(z_near, z_far)], [cx, cy, max(z_near, z_far)], b['d'] / 2)
	fx = [cx - b['d'] / 2, cx + b['d'] / 2, ax, bx]
	fy = [cy - b['d'] / 2, cy + b['d'] / 2, ay, by]
	return boxes, cyl, (min(zs, z_clip), max(zs, z_clip)), [z_near, z_far, z_clip], fx, fy


FIELD_F = [2.44e9]


def part_gap(board, ref, zF):
	"""Box over the gap between the two pads of a 2-pad part on F.Cu (where the part body sits), and its axis."""
	p1, p2 = board['pads'][ref]['pads'][:2]
	a, b = p1['bbox'], p2['bbox']
	d = 0 if abs(p1['c'][0] - p2['c'][0]) > abs(p1['c'][1] - p2['c'][1]) else 1
	lo, hi = sorted([(a[d], a[d + 2]), (b[d], b[d + 2])])
	t0, t1 = max(a[1 - d], b[1 - d]), min(a[3 - d], b[3 - d])
	s, e = [0, 0, zF], [0, 0, zF]
	s[d], e[d] = lo[1], hi[0]
	s[1 - d], e[1 - d] = t0, t1
	return s, e, d


def add_dumps(CSX, board, zF, st, xl, yl, zl, a, zobj, td=True):
	"""Field dumps for pictures and movies (ParaView), from the BSN pipeline. Planes snap to the nearest mesh line.
	TD = time domain E/H on planes (vtk, one file per sample), FD = 2.44 GHz phasors (hdf5, phase movies on the laptop)."""
	o = np.array(board['outline'][0])
	bx0, by0 = o.min(axis=0)
	bx1, by1 = o.max(axis=0)
	X0, X1, Y0, Y1, Z0, Z1 = xl[PML], xl[-PML - 1], yl[PML], yl[-PML - 1], zl[PML], zl[-PML - 1]
	ztop = zF + 0.05                                   # air just above the antenna copper (and the 20 um mask)
	zsub = zF / 2                                      # middle of the board
	zbot = -0.1                                        # between B.Cu and the cell
	s = ant.site(a, board)
	rects, _ = ant.rects(a, board)
	ytop = max(r[3] for r in rects)
	arm_y = ytop - a.get('W', 1.0) / 2                 # centre of the top arm
	ygap = s['y'] + 0.8                                # through the legs, just above the ground edge
	m = 10.0
	planes = {
		'top': ([bx0 - m, by0 - m, ztop], [bx1 + m, by1 + m, ztop]),
		'sub': ([bx0 - 2, by0 - 2, zsub], [bx1 + 2, by1 + 2, zsub]),
		'bot': ([bx0 - 2, by0 - 2, zbot], [bx1 + 2, by1 + 2, zbot]),
		'xz_gap': ([X0, ygap, Z0], [X1, ygap, Z1]),
		'xz_arm': ([X0, arm_y, Z0], [X1, arm_y, Z1]),
		'yz_mid': ([0.0, Y0, Z0], [0.0, Y1, Z1]),
		'yz_feed': ([s['x'], Y0, Z0], [s['x'], Y1, Z1]),
	}
	for n in ('top', 'xz_gap', 'xz_arm', 'yz_mid', 'yz_feed') if td else ():
		CSX.AddDump('td_E_' + n, dump_type=0, dump_mode=2, file_type=0).AddBox(*planes[n])
	if td:
		CSX.AddDump('td_H_top', dump_type=1, dump_mode=1, file_type=0).AddBox(*planes['top'])
	for n, (p0, p1) in planes.items():
		CSX.AddDump('fd_E_' + n, dump_type=10, dump_mode=2, file_type=1, frequency=FIELD_F).AddBox(p0, p1)
		CSX.AddDump('fd_H_' + n, dump_type=11, dump_mode=1, file_type=1, frequency=FIELD_F).AddBox(p0, p1)
	for name, z in st['copper'].items():               # surface current (rot H) on every copper layer
		CSX.AddDump('fd_J_' + name.split('.')[0], dump_type=13, dump_mode=1, file_type=1, frequency=FIELD_F).AddBox(
			[bx0 - 1, by0 - 1, z['z']], [bx1 + 1, by1 + 1, z['z']])
	vol = ([bx0 - 8, by0 - 8, zobj[0] - 8.0], [bx1 + 8, by1 + 8, zobj[1] + 8.0])
	CSX.AddDump('fd_E_vol', dump_type=10, dump_mode=2, file_type=1, frequency=FIELD_F).AddBox(*vol)
	CSX.AddDump('fd_H_vol', dump_type=11, dump_mode=1, file_type=1, frequency=FIELD_F).AddBox(*vol)
	print('field dumps:', {k: [list(map(float, v[0])), list(map(float, v[1]))] for k, v in planes.items()}, flush=True)


def build(case, board, sim_path, threads, want_nf2ff):
	mesh = dict(MESH)
	mesh.update(case.get('mesh', {}))
	st = board['stackup']
	zF = st['copper']['F.Cu']['z']
	zc = sorted(st['copper'][n]['z'] for n in st['copper'])
	mask = case.get('mask', 'none') == 'explicit'
	battery = case.get('battery', False) and bool(board.get('pads', {}).get('BT1'))
	a = case['antenna']
	if not isinstance(a, dict):
		raise SystemExit('antenna must be a parameter dict (the "placed" mode needs a port at the matching network, not built yet)')

	FDTD = openEMS(NrTS=case.get('max_ts', 1000000), EndCriteria=mesh['end'])
	FDTD.SetGaussExcite(F0, FC)
	FDTD.SetBoundaryCond(['PML_%d' % PML] * 6)
	CSX = ContinuousStructure()
	FDTD.SetCSX(CSX)
	grid = CSX.GetGrid()
	grid.SetDeltaUnit(1e-3)

	outline = np.array(board['outline'][0]).T
	diel_at = {}
	for d in st['dielectrics']:
		er = d['er'] * case.get('er_scale', 1.0)
		kappa = 2 * np.pi * F0 * EPS0 * er * d['tand'] * case.get('tand_scale', 1.0)
		m = CSX.AddMaterial(d['name'], epsilon=er, kappa=kappa)
		m.AddLinPoly(outline, 'z', d['z0'], d['z1'] - d['z0'], priority=1)
		diel_at[d['name']] = (d, er, kappa)
	zfix = [d['z0'] for d in st['dielectrics']] + [d['z1'] for d in st['dielectrics']]
	if mask:
		m = CSX.AddMaterial('mask', epsilon=MASK_ER, kappa=2 * np.pi * F0 * EPS0 * MASK_ER * 0.02)
		m.AddLinPoly(outline, 'z', zF, MASK_T, priority=1)
		m.AddLinPoly(outline, 'z', -MASK_T, MASK_T, priority=1)
		zfix += [zF + MASK_T, -MASK_T]

	cu = CSX.AddMetal('Cu')
	for name, polys in board['copper'].items():
		for pts in polys:
			cu.AddPolygon(np.array(pts).T, 'z', st['copper'][name]['z'], priority=10)

	# antenna keep-out: thin boxes of the neighbouring dielectric over every copper layer, priority above the copper
	trace = case.get('ports', 'feed') == 'trace'
	cuts = ant.clear_rects(a, board, notch=not trace)
	eps_z = 1e-3
	for name in st['copper']:
		z = st['copper'][name]['z']
		d = min(st['dielectrics'], key=lambda d: min(abs(d['z0'] - z), abs(d['z1'] - z)))
		_, er, kappa = diel_at[d['name']]
		m = CSX.AddMaterial('cut_' + name.replace('.', '_'), epsilon=er, kappa=kappa)
		for (x0, y0, x1, y1) in cuts:
			m.AddBox([x0, y0, z - eps_z], [x1, y1, z + eps_z], priority=15)

	rects, q = ant.rects(a, board)
	fx, fy = [], []
	for (x0, y0, x1, y1) in rects:
		cu.AddBox([x0, y0, zF], [x1, y1, zF], priority=20)
		fx += [x0, x1]
		fy += [y0, y1]
	for (x0, y0, x1, y1) in cuts:
		fx += [x0, x1]
		fy += [y0, y1]
	if trace:
		tx0, ty0, tx1, ty1 = ant.feed_pad_rect(a, board)      # footprint pad 1, the routed trace ends on it
	else:
		tx0, ty0, tx1, ty1 = ant.port_tab_rect(a, board)      # joins the port's ground end to the board ground
	cu.AddBox([tx0, ty0, zF], [tx1, ty1, zF], priority=20)
	fx += [tx0, tx1]
	fy += [ty0, ty1]

	zobj = (zc[0], zc[-1])
	if battery:
		boxes, (c0, c1, rad), (zb0, zb1), zl_b, bfx, bfy = battery_parts(board, st)
		for s, e in boxes:
			cu.AddBox(s, e, priority=10)
		cu.AddCylinder(c0, c1, rad, priority=10)
		zfix += zl_b
		fx += bfx
		fy += bfy
		zobj = (min(zobj[0], zb0), max(zobj[1], zb1))

	if trace:
		tp = case['trace_port']
		g0, t0, t1, g1 = tp['x']
		py0, py1 = tp['y'] - tp['len'] / 2, tp['y'] + tp['len'] / 2
		subs = [([g0, py0, zF], [t0, py1, zF]), ([g1, py0, zF], [t1, py1, zF])]   # ground -> trace, both sides
		fx += [g0, t0, t1, g1]
		fy += [py0, py1]
		pz = ([g0 - 0.3, g1 + 0.3], [py0 - 0.3, max(py1, ty1) + 0.3])
	else:
		ps, pe, pdir = ant.port_line(a, board)
		ps, pe = ps + [zF], pe + [zF]
		fx += [ps[0], pe[0]]
		fy += [ps[1], pe[1]]

	for ref in list(case.get('parts', {})) + list(case.get('part_ports', [])):   # mesh lines on the part gaps
		s, e, _ = part_gap(board, ref, zF)
		fx += [s[0], e[0]]
		fy += [s[1], e[1]]

	# mesh
	bx0, by0 = outline.min(axis=1)
	bx1, by1 = outline.max(axis=1)
	if battery:
		bx0, bx1 = min(bx0, min(bfx)), max(bx1, max(bfx))
		by0, by1 = min(by0, min(bfy)), max(by1, max(bfy))
	air = mesh['air']
	k0 = cuts[0]
	nt = ant.notch_rect(a, board)
	if trace:                                  # fine mesh over the port, the trace and its gaps up to the antenna
		nt = (pz[0][0], pz[1][0], pz[0][1], max(pz[1][1], nt[3]))
	zones_x = [(k0[0] - 0.5, k0[2] + 0.5, mesh['ant']), (nt[0] - 0.4, nt[2] + 0.4, mesh['port']), (bx0, bx1, mesh['board'])]
	zones_y = [(k0[1] - 0.5, k0[3] + 0.5, mesh['ant']), (nt[1] - 0.4, nt[3] + 0.4, mesh['port']), (by0, by1, mesh['board'])]
	zones_z = []
	for d in st['dielectrics']:
		t = d['z1'] - d['z0']
		zones_z.append((d['z0'], d['z1'], min(mesh['diel'], t / 3)))
	zones_z.append((zc[0] - 0.3, zc[-1] + 0.3, mesh['cu_z']))
	if mask:
		zones_z.append((-MASK_T, zF + MASK_T, MASK_T))
	if battery:
		zones_z.append((zobj[0], zobj[1], 0.5))
	xl = graded_lines([bx0, bx1] + fx, zones_x, bx0 - air, bx1 + air, mesh['max'], mesh['grow'], mesh['merge'])
	yl = graded_lines([by0, by1] + fy, zones_y, by0 - air, by1 + air, mesh['max'], mesh['grow'], mesh['merge'])
	zl = graded_lines(zfix + zc, zones_z, zobj[0] - air, zobj[1] + air, mesh['max'], mesh['grow'], 0.01)
	grid.AddLine('x', xl)
	grid.AddLine('y', yl)
	grid.AddLine('z', zl)

	# vias: drill-size metal barrel where the mesh resolves the hole, else a wire on the nearest mesh line.
	# Vias inside the antenna keep-out are dropped (the keep-out removes their pads too).
	nbox = nwire = 0
	for v in board['vias']:
		if any(x0 <= v['x'] <= x1 and y0 <= v['y'] <= y1 for (x0, y0, x1, y1) in cuts):
			continue
		r = v['drill'] / 2
		inx = xl[(xl > v['x'] - r) & (xl < v['x'] + r)]
		iny = yl[(yl > v['y'] - r) & (yl < v['y'] + r)]
		if len(inx) and len(iny):
			cu.AddBox([v['x'] - r, v['y'] - r, zc[0]], [v['x'] + r, v['y'] + r, zc[-1]], priority=10)
			nbox += 1
		else:
			x = xl[np.argmin(np.abs(xl - v['x']))]
			y = yl[np.argmin(np.abs(yl - v['y']))]
			cu.AddBox([x, y, zc[0]], [x, y, zc[-1]], priority=10)
			nwire += 1
	print('vias: %d as drill-size barrels, %d as wires' % (nbox, nwire), flush=True)

	for ref, pv in case.get('parts', {}).items():
		s, e, d = part_gap(board, ref, zF)
		w = 2 * np.pi * 2.44e9
		if 'L' in pv:
			le = CSX.AddLumpedElement('part_' + ref, ny=d, caps=True, R=w * pv['L'] / pv['Q'], L=pv['L'], LEtype=1)
		else:
			le = CSX.AddLumpedElement('part_' + ref, ny=d, caps=True, R=pv['Q'] / (w * pv['C']), C=pv['C'], LEtype=0)
		le.AddBox(s, e, priority=25)
		print('part %s %s: %s -> %s, dir %d' % (ref, pv, s, e, d), flush=True)
	if case.get('field_dumps', False):
		add_dumps(CSX, board, zF, st, xl, yl, zl, a, zobj, td=case['field_dumps'] != 'fd')

	exc = case.get('excite', 0)                # multi-port runs: 0 = the trace port, k = part_ports[k - 1]
	if trace:
		ports = [FDTD.AddLumpedPort(k + 1, 100, s0, s1, 'x', excite=1.0 if exc == 0 else 0, priority=25)
			for k, (s0, s1) in enumerate(subs)]
	else:
		ports = [FDTD.AddLumpedPort(1, 50, ps, pe, pdir, excite=1.0, priority=25)]
	pports = []
	for j, ref in enumerate(case.get('part_ports', [])):   # 50 ohm ports across the part gaps (multi-port S-matrix)
		s, e, d = part_gap(board, ref, zF)
		pports.append(FDTD.AddLumpedPort(10 + j, 50, s, e, 'xyz'[d], excite=1.0 if exc == j + 1 else 0, priority=25))
		print('part port %s: %s -> %s, dir %s%s' % (ref, s, e, 'xyz'[d], ' (excited)' if exc == j + 1 else ''), flush=True)

	nf2ff = None
	if want_nf2ff:
		m = 8.0
		nf2ff = FDTD.CreateNF2FFBox('nf2ff', [bx0 - m, by0 - m, zobj[0] - m], [bx1 + m, by1 + m, zobj[1] + m],
			frequency=NF2FF_F, over_sampling=NF2FF_OS)
	info = {'cells': [len(xl), len(yl), len(zl)], 'ncells': len(xl) * len(yl) * len(zl),
		'min_cell': [float(np.diff(xl).min()), float(np.diff(yl).min()), float(np.diff(zl).min())]}
	print('mesh', info, flush=True)
	t0 = time.time()
	if not POST_ONLY:
		FDTD.Run(sim_path, verbose=0, numThreads=threads, cleanup=True)
	info['t_run'] = time.time() - t0

	u, i = 0, 0
	for p in ports:                            # parallel sub-ports: voltage averaged, currents summed
		p.CalcPort(sim_path, F)
		u = u + p.uf_tot / len(ports)
		i = i + p.if_tot
	if pports:                                 # V and I of every port of the multi-port set, S-matrix on the laptop
		U, I = [u], [i]
		for p in pports:
			p.CalcPort(sim_path, F)
			U.append(p.uf_tot)
			I.append(p.if_tot)
		np.savez_compressed(os.path.join(os.path.dirname(sim_path), 'ports.npz'), f=F, U=np.array(U), I=np.array(I),
			names=np.array(['radio'] + list(case['part_ports'])), excite=exc)
		u, i = U[exc], I[exc]
	if len(ports) > 1:
		k = int(np.argmin(np.abs(F - 2.44e9)))
		r = ports[1].uf_tot[k] / ports[0].uf_tot[k]
		print('sub-port voltage ratio at 2.44 GHz: %.3f, %.1f deg (expect about 1, 0)' % (abs(r), np.angle(r, deg=True)), flush=True)
	eff = None
	if nf2ff is not None:
		theta = np.arange(0, 181, 5)
		phi = np.arange(0, 361, 5)
		Z0 = 50
		eff, Ds = [], []
		try:
			for k, f in enumerate(NF2FF_F):
				ff = farfield(sim_path, f, theta, phi, center=[(bx0 + bx1) / 2, (by0 + by1) / 2, zF / 2], fidx=k)
				j = int(np.argmin(np.abs(F - f)))
				pacc = 0.5 * np.real(u[j] * np.conj(i[j]))
				pinc = abs((u[j] + Z0 * i[j]) / 2) ** 2 / (2 * Z0)
				eff.append({'f': f, 'Prad': ff['Prad'], 'rad_eff': ff['Prad'] / pacc, 'tot_eff': ff['Prad'] / pinc,
					'Dmax_dBi': ff['Dmax_dBi'], 'flux_eff': ff['flux'] / pacc})
				Ds.append(ff['D_dBi'])
			np.savez_compressed(os.path.join(os.path.dirname(sim_path), 'pattern.npz'), f=np.array(NF2FF_F), theta=theta,
				phi=phi, D_dBi=np.array(Ds))
		except Exception as ex:
			print('far field failed:', repr(ex), flush=True)
			eff = None
	return u, i, eff, info


def band_edges(dB, j, lvl):
	if dB[j] >= lvl:
		return None
	lo = hi = j
	while lo > 0 and dB[lo - 1] < lvl:
		lo -= 1
	while hi < len(F) - 1 and dB[hi + 1] < lvl:
		hi += 1
	return [float(F[lo]), float(F[hi])]


def metrics(s11, Z):
	dB = 20 * np.log10(np.abs(s11))
	m = {}
	j = int(np.argmin(dB))
	m['f_min'], m['s_min'] = float(F[j]), float(dB[j])
	sel = (F >= BLE[0]) & (F <= BLE[1])
	m['ble_worst'] = float(dB[sel].max())
	m['ble_best'] = float(dB[sel].min())
	k = int(np.argmin(np.abs(F - 2.44e9)))
	m['Z_2440'] = [float(Z[k].real), float(Z[k].imag)]
	m['S11_2440_dB'] = float(dB[k])
	m['bw10'] = band_edges(dB, j, -10)
	m['bw6'] = band_edges(dB, j, -6)
	ir = int(np.argmax(Z.real))
	m['f_Rmax'], m['Rmax'] = float(F[ir]), float(Z.real[ir])
	m['Z_fmin'] = [float(Z[j].real), float(Z[j].imag)]
	m['min_interior'] = bool(5 < j < len(F) - 5)
	return m


def main():
	args = [x for x in sys.argv[1:] if x != '--post']
	run_dir = os.path.abspath(args[0])
	threads = int(args[1]) if len(args) > 1 else os.cpu_count()
	case = json.load(open(os.path.join(run_dir, 'case.json')))
	board = json.load(open(os.path.join(HERE, case['board'])))
	errs = ant.check(case['antenna'], board)
	if errs:
		json.dump({'error': errs}, open(os.path.join(run_dir, 'result.json'), 'w'))
		sys.exit('invalid antenna: ' + '; '.join(errs))
	t0 = time.time()
	sim_path = os.path.join(run_dir, 'sim')
	u, i, eff, info = build(case, board, sim_path, threads, case.get('nf2ff', False))
	os.chdir(run_dir)                         # openEMS chdirs into sim_path, which may be deleted below
	if not (case.get('keep_fields', False) or case.get('field_dumps', False)):
		shutil.rmtree(sim_path, ignore_errors=True)
	Z = u / i
	s11 = (Z - 50) / (Z + 50)
	out = {'case': case, 'mesh': info, 't_total': time.time() - t0, 'eff': eff, 'size': ant.size(case['antenna']),
		'length': ant.length(case['antenna']), 'params': ant.params(case['antenna'])}
	out['metrics'] = metrics(s11, Z)
	np.savetxt(os.path.join(run_dir, 'S11.csv'),
		np.column_stack([F, s11.real, s11.imag, 20 * np.log10(np.abs(s11)), Z.real, Z.imag]),
		delimiter=',', header='f_Hz,S11_re,S11_im,S11_dB,Zin_re_ohm,Zin_im_ohm', comments='', fmt='%.6g')
	with open(os.path.join(run_dir, 'result.json'), 'w') as fh:
		json.dump(out, fh, indent=1)
	m = out['metrics']
	if m['s_min'] > -1.0:
		print('WARNING S11 never below -1 dB in %.1f-%.1f GHz: check that the port touches metal at both ends '
			'(2026-11-14: a 0.25 mm gap at the notch bottom gave -0.2 dB on every real-board run)' % (F[0] / 1e9, F[-1] / 1e9), flush=True)
	print('RESULT min %.2f dB @ %.3f GHz, BLE worst %.2f dB, Z2440 %.1f%+.1fj, eff %s, %.0f s' % (
		m['s_min'], m['f_min'] / 1e9, m['ble_worst'], m['Z_2440'][0], m['Z_2440'][1],
		None if not eff else ['%.2f' % e['rad_eff'] for e in eff], out['t_total']), flush=True)


if __name__ == '__main__':
	main()

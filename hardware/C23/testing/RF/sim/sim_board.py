"""openEMS simulation of the C23 rev B board (board.json from export_board.py) with a candidate antenna.

Usage (server, openEMS venv):  python sim_board.py <run_dir> [threads]
<run_dir>/case.json:
    board      path to board.json (relative to this script's folder), or "r011" for the regression model
    antenna    {"family": "ifa"|"fifa", params...} (antenna.py) or "placed" (AE1 copper from board.json)
    ports      "j2"     one port at J2 pad 1 (antenna side of the MM8130 switch), L2 fitted as 0R, L3 open
               "multi"  J2, L2 (series, across the pad gap), L3 (shunt), on b1 also the old antenna-side shunt (then L4) -> S-matrix
               "notch"  r011 only: port across the feed notch
    battery    true: CR2032 and holder clips as metal under B.Cu
    mask       "none" | "explicit" (20 um, er 3.8 on both sides, resolved in z)
    er_scale   multiplies all dielectric er (sensitivity)
    nf2ff      true: radiation efficiency at NF2FF_F (J2 excitation)
    mesh       overrides of MESH below
Writes <run_dir>/result.json, S11.csv (J2), and for "multi" S<n>P.s<n>p (all pairs of a frequency on one line). openEMS field data is deleted after use.
"""
import json
import os
import sys
import time

import numpy as np
from CSXCAD import ContinuousStructure
from openEMS import openEMS
from openEMS.physical_constants import EPS0

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import antenna as ant  # noqa: E402
from sim_ports import pad, port_defs  # noqa: E402
from farfield import farfield  # noqa: E402

F0, FC = 2.45e9, 1.0e9
F = np.linspace(1.9e9, 3.0e9, 1101)
NF2FF_F = [2.40e9, 2.44e9, 2.48e9]
BLE = (2.400e9, 2.4835e9)
MESH = {'ant': 0.25, 'rf': 0.13, 'rf_y': 0.15, 'board': 0.8, 'max': 4.0, 'air': 30.0, 'grow': 1.3, 'prepreg': 0.106,
	'core': 0.18, 'merge': 0.09, 'end': 1e-4}
RF_WIN_X = (-7.6, -4.2)       # J2 / L2 / L3 / feed area, fine mesh
RF_WIN_Y = (2.4, 11.2)
ANT_WIN_X = (-11.5, 10.5)
ANT_WIN_Y = (9.5, 17.0)
MASK_T, MASK_ER = 0.02, 3.8
NF2FF_OS = 4          # time oversampling of the far-field dumps (openEMS FD dumps default to the bare Nyquist rate)
PML = 8
POST_ONLY = '--post' in sys.argv     # re-evaluate an existing sim folder without running FDTD


def graded_lines(fixed, zones, lo, hi, maxc, grow, merge):
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


def r011_board():
	"""The 40 x 41 x 1.5 mm two-layer test board of the r011 optimizer run, moved so the feed is at FEED_X, GND_Y."""
	dx, dy = ant.FEED_X - 8.5, ant.GND_Y - 33.0
	x0, x1, y0, y1 = dx, 40 + dx, dy, 41 + dy
	n0, n1 = 7.0 + dx, 10.0 + dx
	g = ant.GND_Y
	gnd = [[x0, y0], [x1, y0], [x1, g], [n1, g], [n1, g - 1], [n0, g - 1], [n0, g], [x0, g]]
	return {
		'stackup': {'copper': {'F.Cu': {'z': 1.5}}, 'dielectrics': [{'name': 'FR4', 'z0': 0, 'z1': 1.5, 'er': 4.4, 'tand': 0.02}]},
		'outline': [[[x0, y0], [x1, y0], [x1, y1], [x0, y1]]],
		'copper': {'F.Cu': [gnd]}, 'vias': [], 'pads': {}, 'ae1': None,
	}


def build(case, board, excite_group, sim_path, threads, want_nf2ff):
	mesh = dict(MESH)
	mesh.update(case.get('mesh', {}))
	st = board['stackup']
	zF = st['copper']['F.Cu']['z']
	er_scale = case.get('er_scale', 1.0)
	mask = case.get('mask', 'none') == 'explicit'
	battery = case.get('battery', False)
	r011 = case['board'] == 'r011'

	FDTD = openEMS(NrTS=case.get('max_ts', 2000000), EndCriteria=mesh['end'])
	FDTD.SetGaussExcite(F0, FC)
	FDTD.SetBoundaryCond(['PML_%d' % PML] * 6)
	CSX = ContinuousStructure()
	FDTD.SetCSX(CSX)
	grid = CSX.GetGrid()
	grid.SetDeltaUnit(1e-3)

	outline = np.array(board['outline'][0]).T
	for d in st['dielectrics']:
		er = d['er'] * er_scale
		m = CSX.AddMaterial(d['name'], epsilon=er, kappa=2 * np.pi * F0 * EPS0 * er * d['tand'] * case.get('tand_scale', 1.0))
		m.AddLinPoly(outline, 'z', d['z0'], d['z1'] - d['z0'], priority=1)
	zfix = [d['z0'] for d in st['dielectrics']] + [d['z1'] for d in st['dielectrics']]
	if mask:
		m = CSX.AddMaterial('mask', epsilon=MASK_ER, kappa=2 * np.pi * F0 * EPS0 * MASK_ER * 0.02)
		m.AddLinPoly(outline, 'z', zF, MASK_T, priority=1)
		m.AddLinPoly(outline, 'z', -MASK_T, MASK_T, priority=1)
		zfix += [zF + MASK_T, -MASK_T]

	cu = CSX.AddMetal('Cu')
	for name, polys in board['copper'].items():
		z = st['copper'][name]['z']
		for pts in polys:
			cu.AddPolygon(np.array(pts).T, 'z', z, priority=10)

	# antenna
	fx, fy = [], []
	a = case['antenna']
	if a == 'placed':
		for pts in board['ae1']['copper']:
			cu.AddPolygon(np.array(pts).T, 'z', zF, priority=10)
			fx += [p[0] for p in pts]
			fy += [p[1] for p in pts]
	else:
		rects, _ = ant.rects(a)
		if r011:
			rects[1] = (rects[1][0], ant.GND_Y, rects[1][2], rects[1][3])   # r011 feed leg starts at the ground edge
			rects[0] = (rects[0][0], ant.GND_Y, rects[0][2], rects[0][3])
		for (x0, y0, x1, y1) in rects:
			cu.AddBox([x0, y0, zF], [x1, y1, zF], priority=10)
			fx += [x0, x1]
			fy += [y0, y1]

	ant_fy_min = min(fy)

	# 0R at L2 for the J2 port mode
	if case['ports'] == 'j2':
		a2, c2 = pad(board, 'L2', '1')['bbox'], pad(board, 'L2', '2')['bbox']
		cu.AddBox([max(a2[0], c2[0]), min(a2[1], c2[1]), zF], [min(a2[2], c2[2]), max(a2[3], c2[3]), zF], priority=10)

	# battery: CR2032 (20 mm, 3.2 mm) 0.5 mm under B.Cu, holder clips to BT1 pads
	if battery:
		bx, by = board['pads']['BT1']['pos']
		zb0, zb1 = -0.5, -3.7
		cu.AddCylinder([bx, by, zb1], [bx, by, zb0], 10.0, priority=10)
		pv = pad(board, 'BT1', '1')['c']
		pg = pad(board, 'BT1', '2')['c']
		cu.AddBox([pv[0], pv[1] - 1.5, 0], [pv[0], pv[1] + 1.5, zb1 - 0.2], priority=10)          # + clip, vertical
		cu.AddBox([bx, pv[1] - 1.5, zb1 - 0.2], [pv[0], pv[1] + 1.5, zb1 - 0.2], priority=10)      # + clip over the can
		cu.AddBox([pg[0], pg[1] - 1.5, 0], [pg[0], pg[1] + 1.5, zb0], priority=10)                # - contact, vertical
		cu.AddBox([pg[0], pg[1] - 1.5, zb0], [bx - 3, pg[1] + 1.5, zb0], priority=10)             # - contact under the cell
		zfix += [zb0, zb1, zb1 - 0.2]
		fx += [pv[0], pg[0], bx, bx - 3]
		fy += [pv[1] - 1.5, pv[1] + 1.5]

	groups = port_defs(board, case['ports'], zF)
	px, py = [], []
	for _, subs in groups:
		for s, e, _, _ in subs:
			px += [s[0], e[0]]
			py += [s[1], e[1]]

	# mesh
	bx0, by0 = outline.min(axis=1)
	bx1, by1 = outline.max(axis=1)
	air = mesh['air']
	zones_x = [(*ANT_WIN_X, mesh['ant']), (*RF_WIN_X, mesh['rf']), (bx0, bx1, mesh['board'])]
	ant_y0 = ANT_WIN_Y[0] if a == 'placed' or not isinstance(a, dict) else min(ANT_WIN_Y[0], ant.base(a)['GND_Y'] - 1.1)
	if a == 'placed':
		ant_y0 = min(ANT_WIN_Y[0], ant_fy_min - 0.3)
	zones_y = [(ant_y0, ANT_WIN_Y[1], mesh['ant']), (*RF_WIN_Y, mesh['rf_y']), (by0, by1, mesh['board'])]
	zc = sorted(st['copper'][n]['z'] for n in st['copper'])
	zones_z = []
	for d in st['dielectrics']:
		t = d['z1'] - d['z0']
		zones_z.append((d['z0'], d['z1'], mesh['prepreg'] if t < 0.5 else mesh['core']))
	if r011:
		zones_z = [(1.2, 1.8, 0.1), (0, 1.5, 0.3)]
	if mask:
		zones_z.append((-MASK_T, zF + MASK_T, MASK_T))
	if battery:
		zones_z.append((-3.9, -0.5, 0.5))
	zones_z.append((zc[0] - 0.3, zc[-1] + 0.3, mesh['prepreg']))
	zlo = (-3.9 if battery else 0) - air
	xl = graded_lines([bx0, bx1] + fx + px, zones_x, bx0 - air, bx1 + air, mesh['max'], mesh['grow'], mesh['merge'])
	yl = graded_lines([by0, by1] + fy + py, zones_y, by0 - air, by1 + air, mesh['max'], mesh['grow'], mesh['merge'])
	zl = graded_lines(zfix + zc, zones_z, zlo, zc[-1] + air, mesh['max'], mesh['grow'], 0.01)
	grid.AddLine('x', xl)
	grid.AddLine('y', yl)
	grid.AddLine('z', zl)

	# vias: solid metal barrel of the drill size (the plated hole), as a square of side = drill. Where the mesh
	# has no line inside the hole (coarse areas), a wire on the nearest mesh line instead.
	nbox = 0
	for v in board['vias']:
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
	print('vias: %d as drill-size barrels, %d as wires' % (nbox, len(board['vias']) - nbox), flush=True)

	ports = []
	nport = 0
	for gi, (name, subs) in enumerate(groups):
		lst = []
		for s, e, d, R in subs:
			nport += 1
			lst.append(FDTD.AddLumpedPort(nport, R, s, e, d,
				excite=1.0 if gi == excite_group else 0, priority=20))
		ports.append(lst)

	nf2ff = None
	if want_nf2ff:
		m = 8.0
		nf2ff = FDTD.CreateNF2FFBox('nf2ff', [bx0 - m, by0 - m, zlo + air - m], [bx1 + m, by1 + m, zc[-1] + m],
			frequency=NF2FF_F, over_sampling=NF2FF_OS)
	info = {'cells': [len(xl), len(yl), len(zl)], 'ncells': len(xl) * len(yl) * len(zl),
		'min_cell': [float(np.diff(xl).min()), float(np.diff(yl).min()), float(np.diff(zl).min())]}
	print('mesh', info, flush=True)
	t0 = time.time()
	if not POST_ONLY:
		FDTD.Run(sim_path, verbose=0, numThreads=threads, cleanup=True)
	info['t_run'] = time.time() - t0

	VI = []
	k = int(np.argmin(np.abs(F - 2.44e9)))
	for lst in ports:
		u, i = 0, 0
		for p in lst:
			p.CalcPort(sim_path, F)
			u = u + p.uf_tot / len(lst)
			i = i + p.if_tot
		if len(lst) > 1:
			info['subport_u_ratio_2440'] = [float(abs(lst[1].uf_tot[k] / lst[0].uf_tot[k])),
				float(np.angle(lst[1].uf_tot[k] / lst[0].uf_tot[k], deg=True))]
		VI.append((u, i))
	eff = None
	if nf2ff is not None:
		# Far field from our own transform (farfield.py). The openEMS C++ NF2FF result is kept as Prad_openems
		# for reference only: it was box-size dependent and far too low for layered boards (see farfield.py).
		theta = np.arange(0, 181, 5)
		phi = np.arange(0, 361, 5)
		u, i = VI[excite_group]
		Z0 = 50
		eff = []
		Ds = []
		try:
			res = nf2ff.CalcNF2FF(sim_path, NF2FF_F, theta, phi, center=[0, 0, zF / 2], read_cached=False)
			p_oe = [float(x) for x in res.Prad]
		except Exception as ex:
			print('openEMS NF2FF failed:', repr(ex), flush=True)
			p_oe = [float('nan')] * len(NF2FF_F)
		try:
			for k, f in enumerate(NF2FF_F):
				ff = farfield(sim_path, f, theta, phi, center=[0, 0, zF / 2], fidx=k)
				j = int(np.argmin(np.abs(F - f)))
				pacc = 0.5 * np.real(u[j] * np.conj(i[j]))
				ainc = (u[j] + Z0 * i[j]) / 2
				pinc = abs(ainc) ** 2 / (2 * Z0)
				eff.append({'f': f, 'Prad': ff['Prad'], 'rad_eff': ff['Prad'] / pacc, 'tot_eff': ff['Prad'] / pinc,
					'Dmax_dBi': ff['Dmax_dBi'], 'flux_eff': ff['flux'] / pacc, 'Prad_openems_eff': p_oe[k] / pacc})
				Ds.append(ff['D_dBi'])
			np.savez_compressed(os.path.join(os.path.dirname(sim_path), 'pattern.npz'), f=np.array(NF2FF_F), theta=theta,
				phi=phi, D_dBi=np.array(Ds))
		except Exception as ex:
			print('far field failed:', repr(ex), flush=True)
			eff = None
	return VI, eff, info, [g[0] for g in groups]


def metrics(s11, Z):
	dB = 20 * np.log10(np.abs(s11))
	m = {}
	j = int(np.argmin(dB))
	m['f_min'], m['s_min'] = float(F[j]), float(dB[j])
	sel = (F >= BLE[0]) & (F <= BLE[1])
	m['ble_worst'] = float(dB[sel].max())
	m['ble_best'] = float(dB[sel].min())
	for lo, hi, key in ((2.38e9, 2.52e9, 'goal_worst'),):
		sel = (F >= lo) & (F <= hi)
		m[key] = float(dB[sel].max())
	k = int(np.argmin(np.abs(F - 2.44e9)))
	m['Z_2440'] = [float(Z[k].real), float(Z[k].imag)]
	m['S11_2440_dB'] = float(dB[k])
	bw = None
	if dB[j] < -10:
		lo, hi = j, j
		while lo > 0 and dB[lo - 1] < -10:
			lo -= 1
		while hi < len(F) - 1 and dB[hi + 1] < -10:
			hi += 1
		bw = [float(F[lo]), float(F[hi])]
	m['bw10'] = bw
	bw6 = None
	if dB[j] < -6:
		lo, hi = j, j
		while lo > 0 and dB[lo - 1] < -6:
			lo -= 1
		while hi < len(F) - 1 and dB[hi + 1] < -6:
			hi += 1
		bw6 = [float(F[lo]), float(F[hi])]
	m['bw6'] = bw6
	R = Z.real
	i = int(np.argmax(R))
	m['f_Rmax'], m['Rmax'] = float(F[i]), float(R[i])
	m['min_interior'] = bool(5 < j < len(F) - 5)
	return m


def main():
	args = [a for a in sys.argv[1:] if a != '--post']
	run_dir = os.path.abspath(args[0])
	threads = int(args[1]) if len(args) > 1 else os.cpu_count()
	case = json.load(open(os.path.join(run_dir, 'case.json')))
	if case['board'] == 'r011':
		board = r011_board()
	else:
		board = json.load(open(os.path.join(HERE, case['board'])))
	if case['antenna'] != 'placed':
		errs = ant.check(case['antenna']) if case['board'] != 'r011' else []
		if errs:
			json.dump({'error': errs}, open(os.path.join(run_dir, 'result.json'), 'w'))
			sys.exit('invalid antenna: ' + '; '.join(errs))
	t0 = time.time()
	ngroups = len(port_defs(board, case['ports'], board['stackup']['copper']['F.Cu']['z']))
	VIs, eff, info = [], None, None
	for e in range(ngroups):
		sim_path = os.path.join(run_dir, 'sim_e%d' % e)
		VI, ef, info, names = build(case, board, e, sim_path, threads, case.get('nf2ff', False) and e == 0)
		VIs.append(VI)
		if e == 0:
			eff = ef
		os.chdir(run_dir)                 # openEMS chdirs into sim_path, which is deleted below
		if not case.get('keep_fields', False):
			import shutil
			shutil.rmtree(sim_path, ignore_errors=True)

	Z0 = 50.0
	out = {'case': case, 'mesh': info, 't_total': time.time() - t0, 'eff': eff}
	if ngroups == 1:
		u, i = VIs[0][0]
		Z = u / i
		s11 = (Z - Z0) / (Z + Z0)
		out['ports'] = names
	else:
		# S = B A^-1 from all excitations, waves a = (V + Z0 I) / 2, b = (V - Z0 I) / 2
		n = ngroups
		S = np.zeros((len(F), n, n), complex)
		A = np.zeros((len(F), n, n), complex)
		B = np.zeros((len(F), n, n), complex)
		for e in range(n):
			for p in range(n):
				u, i = VIs[e][p]
				A[:, p, e] = (u + Z0 * i) / 2
				B[:, p, e] = (u - Z0 * i) / 2
		S = B @ np.linalg.inv(A)
		s11 = S[:, 0, 0]
		Z = Z0 * (1 + s11) / (1 - s11)
		out['ports'] = names
		# Touchstone, n ports, every frequency on one line (row-major S matrix), port order in the header
		with open(os.path.join(run_dir, 'S%dP.s%dp' % (n, n)), 'w') as fh:
			fh.write('! C23 board, ports %s\n# Hz S RI R 50\n' % ' '.join(names))
			for k, f in enumerate(F):
				fh.write('%.6e ' % f + ' '.join('%.6e %.6e' % (S[k, r, c].real, S[k, r, c].imag) for r in range(n) for c in range(n)) + '\n')
	out['metrics'] = metrics(s11, Z)
	np.savetxt(os.path.join(run_dir, 'S11.csv'),
		np.column_stack([F, s11.real, s11.imag, 20 * np.log10(np.abs(s11)), Z.real, Z.imag]),
		delimiter=',', header='f_Hz,S11_re,S11_im,S11_dB,Zin_re_ohm,Zin_im_ohm', comments='', fmt='%.6g')
	# sanity: J2 sub-port voltages should agree
	with open(os.path.join(run_dir, 'result.json'), 'w') as fh:
		json.dump(out, fh, indent=1)
	m = out['metrics']
	print('RESULT min %.2f dB @ %.3f GHz, BLE worst %.2f dB, Z2440 %.1f%+.1fj, eff %s, %.0f s' % (
		m['s_min'], m['f_min'] / 1e9, m['ble_worst'], m['Z_2440'][0], m['Z_2440'][1],
		None if not eff else ['%.2f' % e['rad_eff'] for e in eff], out['t_total']), flush=True)


if __name__ == '__main__':
	main()

"""Minimal IFA test bench for checking the simulation method (runs locally, a few minutes per case).

A printed IFA on a rectangular ground plane. Everything is zero-thickness PEC on one plane (z = 0). Optional
FR4 slab under it. A single lumped port across a small gap between the ground edge and the feed leg. The mesh
grading and the NF2FF efficiency evaluation are the same as in sim_board.py.

Geometry (mm): ground x -GX/2..GX/2, y -GY..0 (edge at y = 0). Feed leg centred at x = 0 from y = gap to the arm.
Short leg centred at x = -S (centre to centre). Arm bottom at y = H, width Wa, from the short leg to x = L.

Usage: python simple_ifa.py <out_dir> <case.json | inline json> [threads]
  keys: GX GY H L S Wa Wf Ws gap sub (none|fr4) er tand t_sub mesh_ant mesh_max air nf_margin end fc tag
        stack (1L | 4L: the C23 stack-up, ground on all four layers, via fence at the ground edge and a 5 mm via
        grid, FR4 everywhere incl. under the antenna; sub/t_sub are ignored) battery (PEC disc r 10, 3.2 mm thick,
        0.5 mm under the board, centred on the ground) via_pitch
Prints and writes <out_dir>/<tag>.json with Z(f) at 2.45 GHz, the S11 minimum, -10 dB band, efficiency, Dmax.
"""
import json
import os
import shutil
import sys

import numpy as np
from CSXCAD import ContinuousStructure
from openEMS import openEMS
from openEMS.physical_constants import EPS0

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sim_board import graded_lines  # noqa: E402

DEF = {'GX': 40.0, 'GY': 30.0, 'H': 3.0, 'L': 22.0, 'S': 3.0, 'Wa': 1.0, 'Wf': 1.0, 'Ws': 1.0, 'gap': 0.5,
	'sub': 'none', 'er': 4.4, 'tand': 0.0, 't_sub': 1.5, 'mesh_ant': 0.25, 'mesh_max': 4.0, 'air': 30.0,
	'nf_margin': 8.0, 'end': 1e-5, 'stack': '1L', 'battery': False, 'via_pitch': 1.0, 'gnd_layers': [0, 1, 2], 'vias': True, 'er4': 4.4, 'mesh_z_board': 0.1, 'keep': False, 'nf_os': 0, 'f0': 2.45e9, 'fc': 1.0e9, 'grow': 1.3, 'tag': 'case'}
F = np.linspace(1.5e9, 3.5e9, 2001)
NF_F = [2.45e9]


def run(p, out, threads):
	q = dict(DEF)
	q.update(p)
	sim = os.path.join(out, 'sim_' + q['tag'])
	shutil.rmtree(sim, ignore_errors=True)
	FDTD = openEMS(NrTS=1000000, EndCriteria=q['end'])
	FDTD.SetGaussExcite(q['f0'], q['fc'])
	FDTD.SetBoundaryCond(['PML_8'] * 6)
	CSX = ContinuousStructure()
	FDTD.SetCSX(CSX)
	grid = CSX.GetGrid()
	grid.SetDeltaUnit(1e-3)
	cu = CSX.AddMetal('pec')

	GX, GY, H, L, S = q['GX'], q['GY'], q['H'], q['L'], q['S']
	Wa, Wf, Ws, gap = q['Wa'], q['Wf'], q['Ws'], q['gap']
	ya0, ya1 = H, H + Wa
	xs0, xs1 = -S - Ws / 2, -S + Ws / 2
	rects = [(-GX / 2, -GY, GX / 2, 0),          # ground
		(xs0, 0, xs1, ya1),                      # short leg
		(-Wf / 2, gap, Wf / 2, ya0),             # feed leg
		(xs0, ya0, L, ya1)]                      # arm
	zF = 0.0
	vias = []
	zfix = [0]
	zlo_struct = 0.0
	if q['stack'] == '4L':
		zs = [0.0, 0.2104, 1.2754, 1.4858]
		zF = zs[-1]
		zfix = list(zs)
		kappa = 2 * np.pi * q['f0'] * EPS0 * q['er4'] * q['tand']
		fr4 = CSX.AddMaterial('fr4', epsilon=q['er4'], kappa=kappa)
		fr4.AddBox([-GX / 2, -GY, 0], [GX / 2, ya1 + 1.0, zF], priority=1)
		for li in q['gnd_layers']:
			cu.AddBox([-GX / 2, -GY, zs[li]], [GX / 2, 0, zs[li]], priority=10)
		r = 0.15
		vx = list(np.arange(-GX / 2 + 0.5, GX / 2 - 0.4, q['via_pitch']))
		vias = [(x, -0.4) for x in vx if abs(x) > Wf / 2 + 0.5]
		vias += [(x, y) for x in np.arange(-GX / 2 + 2.5, GX / 2, 5.0) for y in np.arange(-5.0, -GY, -5.0)]
		if not q['vias']:
			vias = []
		for x, y in vias:
			cu.AddBox([x - r, y - r, 0], [x + r, y + r, zF], priority=10)
		zlo_struct = 0.0
	elif q['sub'] == 'fr4':
		kappa = 2 * np.pi * q['f0'] * EPS0 * q['er'] * q['tand']
		fr4 = CSX.AddMaterial('fr4', epsilon=q['er'], kappa=kappa)
		fr4.AddBox([-GX / 2, -GY, -q['t_sub']], [GX / 2, ya1 + 1.0, 0], priority=1)
		zfix += [-q['t_sub']]
		zlo_struct = -q['t_sub']
	for x0, y0, x1, y1 in rects:
		cu.AddBox([x0, y0, zF], [x1, y1, zF], priority=10)
	if q['battery']:
		cu.AddCylinder([0, -GY / 2, zlo_struct - 3.7], [0, -GY / 2, zlo_struct - 0.5], 10.0, priority=10)
		zfix += [zlo_struct - 3.7, zlo_struct - 0.5]
		zlo_struct -= 3.7
	port = FDTD.AddLumpedPort(1, 50, [-Wf / 2, 0, zF], [Wf / 2, gap, zF], 'y', excite=1.0, priority=20)

	m = q['mesh_ant']
	fx = sorted({r[0] for r in rects} | {r[2] for r in rects} | {v[0] for v in vias})
	fy = sorted({r[1] for r in rects} | {r[3] for r in rects} | {v[1] for v in vias})
	zx = [(xs0 - 2, L + 2, m), (-GX / 2, GX / 2, 1.0)]
	zy = [(-2, ya1 + 2, m), (-GY, 0, 1.0)]
	zz = [(min(zfix) - 0.5, max(zfix) + 0.5, m)] + ([(0, zF, q['mesh_z_board'])] if q['stack'] == '4L' else [])
	if q['battery']:
		zz.append((zlo_struct, zlo_struct + 3.2, 0.5))
	air = q['air']
	xl = graded_lines(fx, zx, -GX / 2 - air, GX / 2 + air, q['mesh_max'], q['grow'], 0.05)
	yl = graded_lines(fy, zy, -GY - air, ya1 + air, q['mesh_max'], q['grow'], 0.05)
	zl = graded_lines(zfix, zz, zlo_struct - air, zF + air, q['mesh_max'], q['grow'], 0.05)
	grid.AddLine('x', xl)
	grid.AddLine('y', yl)
	grid.AddLine('z', zl)
	mg = q['nf_margin']
	nf = FDTD.CreateNF2FFBox('nf2ff', [-GX / 2 - mg, -GY - mg, zlo_struct - mg], [GX / 2 + mg, ya1 + mg, zF + mg], frequency=NF_F,
		**({'over_sampling': q['nf_os']} if q['nf_os'] else {}))
	ncell = len(xl) * len(yl) * len(zl)
	FDTD.Run(sim, verbose=0, numThreads=threads, cleanup=True)

	port.CalcPort(sim, F)
	u, i = port.uf_tot, port.if_tot
	Z = u / i
	s11 = (Z - 50) / (Z + 50)
	dB = 20 * np.log10(np.abs(s11))
	k = int(np.argmin(np.abs(F - 2.45e9)))
	kmin = int(np.argmin(dB))
	band = F[dB < -10]
	res = nf.CalcNF2FF(sim, NF_F, np.arange(0, 181, 3), np.arange(0, 361, 5), center=[0, -GY / 2, zF / 2], read_cached=False)
	pacc = 0.5 * np.real(u[k] * np.conj(i[k]))
	# resonance: where X crosses zero going up (series-like) closest to the S11 minimum
	sgn = np.where(np.diff(np.sign(Z.imag)) != 0)[0]
	fres = [float(F[j]) for j in sgn]
	r = {'tag': q['tag'], 'params': {kk: q[kk] for kk in ('GX', 'GY', 'H', 'L', 'S', 'Wa', 'sub', 'tand', 'mesh_ant', 'nf_margin', 'end', 'stack', 'battery')},
		'ncell': ncell, 'Z245': [float(Z[k].real), float(Z[k].imag)], 'f_min': float(F[kmin]), 's_min': float(dB[kmin]),
		'Z_at_min': [float(Z[kmin].real), float(Z[kmin].imag)], 'bw10': [float(band.min()), float(band.max())] if len(band) else None,
		'X_zero_f': fres, 'R_at_X_zero': [float(Z[j].real) for j in sgn],
		'rad_eff_245': float(res.Prad[0] / pacc), 'Dmax_dBi_245': float(10 * np.log10(res.Dmax[0]))}
	np.savetxt(os.path.join(out, q['tag'] + '_Z.csv'), np.c_[F, Z.real, Z.imag], delimiter=',', header='f,R,X', comments='')
	json.dump(r, open(os.path.join(out, q['tag'] + '.json'), 'w'), indent=1)
	if not q['keep']:
		shutil.rmtree(sim, ignore_errors=True)
	r['P_acc'] = float(pacc)
	r['Prad_nf2ff'] = float(res.Prad[0])
	json.dump(r, open(os.path.join(out, q['tag'] + '.json'), 'w'), indent=1)
	print('%-14s cells %7d | Z(2.45) %6.1f%+7.1fj | S11 min %6.1f @ %.3f (Z %5.1f%+6.1fj) | X=0 at %s R %s | eff %.3f Dmax %.2f dBi' % (
		q['tag'], ncell, Z[k].real, Z[k].imag, dB[kmin], F[kmin] / 1e9, Z[kmin].real, Z[kmin].imag,
		['%.3f' % (f / 1e9) for f in fres], ['%.0f' % x for x in r['R_at_X_zero']], r['rad_eff_245'], r['Dmax_dBi_245']), flush=True)
	return r


if __name__ == '__main__':
	out = os.path.abspath(sys.argv[1])
	os.makedirs(out, exist_ok=True)
	a = sys.argv[2]
	cases = json.load(open(a)) if os.path.exists(a) else json.loads(a)
	thr = int(sys.argv[3]) if len(sys.argv) > 3 else 8
	for c in (cases if isinstance(cases, list) else [cases]):
		run(c, out, thr)

"""Matched result of a multi-port run set (sim_board.py case keys part_ports + excite), BSN-N52 r7 2026-11-15.

The four runs of one set differ only in the excited port: 0 = radio port (trace port beside the radio side of L2),
1..3 = 50 ohm ports across the L2, C1, L1 pad gaps. Every run saves V and I of all ports (ports.npz).
openEMS lumped L / C elements grew without bound after the pulse (smoke run 11afcc8780), so the parts are added here:

    a = (V + Z0 I) / (2 sqrt Z0), b = (V - Z0 I) / (2 sqrt Z0)      per port and run (Z0 = 50 ohm)
    S = B A^-1                                                        4 x 4 per frequency, pads and traces included
    parts as loads a_k = G_k b_k (k = L2, C1, L1), radio port driven with a_1 = 1:
    b_r = (1 - S_rr G)^-1 S_r1,  Gin = S_11 + S_1r G b_r
    power in part k = (|b_k|^2 - |a_k|^2) / 2, incident power 1/2 (peak phasors, like sim_board.py)

The matched fields are the weighted sum of the four runs: c = A^-1 a* with a* = [1, a_r] the port waves of the
matched network. That gives the 2.44 GHz field dumps (same hdf5 layout, written to <out>/fd_*.h5) and the far field
from the superposed NF2FF face currents (farfield.load_faces of every run), so total efficiency = Prad / P_inc
includes mismatch, part loss, board and battery loss.

Part models from match_tee.py (L: series R = wL/Q and self capacitance CP, C: ESR from Q and ESL).

Usage (server):  python combine_multi.py <out dir> <run0> <run1> <run2> <run3>
                 [--L2 3.3e-9] [--C1 1e-12] [--L1 5.1e-9] [--QL 50] [--QC 100] [--CP 0.08e-12] [--ESL 0.3e-9] [--nofields]
"""
import argparse
import glob
import json
import os
import shutil
import sys

import h5py
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from farfield import load_faces, C0, ETA0  # noqa: E402
from sim_board import NF2FF_F, FIELD_F  # noqa: E402

Z0 = 50.0


def z_ind(L, w, Q, CP):
	z = 1j * w * L + w * L / Q
	return 1 / (1 / z + 1j * w * CP) if CP else z


def z_cap(C, w, Q, ESL):
	return 1 / (1j * w * C) + 1 / (w * C * Q) + 1j * w * ESL


def waves(U, I):
	return (U + Z0 * I) / (2 * np.sqrt(Z0)), (U - Z0 * I) / (2 * np.sqrt(Z0))


def far(P, w, J, M, f, center, theta_deg, phi_deg, chunk=400):
	"""farfield.farfield on given face currents (copy of its core, J and M already superposed)."""
	P = P - np.asarray(center, float) * 1e-3
	k = 2 * np.pi * f / C0
	th = np.deg2rad(np.asarray(theta_deg, float))
	ph = np.deg2rad(np.asarray(phi_deg, float))
	TH, PH = np.meshgrid(th, ph, indexing='ij')
	t, p = TH.ravel(), PH.ravel()
	r = np.stack([np.sin(t) * np.cos(p), np.sin(t) * np.sin(p), np.cos(t)], 1)
	et = np.stack([np.cos(t) * np.cos(p), np.cos(t) * np.sin(p), -np.sin(t)], 1)
	ep = np.stack([-np.sin(p), np.cos(p), np.zeros_like(p)], 1)
	Jw, Mw = J * w[:, None], M * w[:, None]
	U = np.zeros(len(t))
	for a in range(0, len(t), chunk):
		e = np.exp(1j * k * (r[a:a + chunk] @ P.T))
		N, L = e @ Jw, e @ Mw
		Nt, Np = np.sum(N * et[a:a + chunk], 1), np.sum(N * ep[a:a + chunk], 1)
		Lt, Lp = np.sum(L * et[a:a + chunk], 1), np.sum(L * ep[a:a + chunk], 1)
		U[a:a + chunk] = k ** 2 / (32 * np.pi ** 2 * ETA0) * (np.abs(Lp + ETA0 * Nt) ** 2 + np.abs(Lt - ETA0 * Np) ** 2)
	U = U.reshape(TH.shape)
	Prad = np.trapezoid(np.trapezoid(U * np.sin(TH), ph, axis=1), th)
	D = 4 * np.pi * U / Prad
	return float(Prad), 10 * np.log10(np.maximum(D, 1e-12))


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('out')
	ap.add_argument('runs', nargs=4)
	ap.add_argument('--L2', type=float, default=3.3e-9)
	ap.add_argument('--C1', type=float, default=1.0e-12)
	ap.add_argument('--L1', type=float, default=5.1e-9)
	ap.add_argument('--QL', type=float, default=50.0)
	ap.add_argument('--QC', type=float, default=100.0)
	ap.add_argument('--CP', type=float, default=0.08e-12)
	ap.add_argument('--ESL', type=float, default=0.3e-9)
	ap.add_argument('--nofields', action='store_true')
	a = ap.parse_args()
	os.makedirs(a.out, exist_ok=True)

	d = [np.load(os.path.join(r, 'ports.npz')) for r in a.runs]
	assert [int(x['excite']) for x in d] == [0, 1, 2, 3], [int(x['excite']) for x in d]
	names = [str(n) for n in d[0]['names']]
	assert names == ['radio', 'L2', 'C1', 'L1'], names
	f = d[0]['f']
	U = np.stack([x['U'] for x in d], 2)               # (port, f, run)
	I = np.stack([x['I'] for x in d], 2)
	A, B = waves(U, I)
	A, B = A.transpose(1, 0, 2), B.transpose(1, 0, 2)  # (f, port, run)
	S = B @ np.linalg.inv(A)                           # (f, 4, 4)
	w = 2 * np.pi * f
	ZL = np.stack([z_ind(a.L2, w, a.QL, a.CP), z_cap(a.C1, w, a.QC, a.ESL), z_ind(a.L1, w, a.QL, a.CP)], 1)
	G = (ZL - Z0) / (ZL + Z0)                          # (f, 3)
	n = len(f)
	gin = np.zeros(n, complex)
	astar = np.zeros((n, 4), complex)
	ploss = np.zeros((n, 3))
	for j in range(n):
		s = S[j]
		Gd = np.diag(G[j])
		br = np.linalg.solve(np.eye(3) - s[1:, 1:] @ Gd, s[1:, 0])
		ar = G[j] * br
		gin[j] = s[0, 0] + s[0, 1:] @ ar
		astar[j] = np.r_[1.0, ar]
		ploss[j] = (np.abs(br) ** 2 - np.abs(ar) ** 2)       # / 2, relative to the incident 1/2: fraction of P_inc
	c = np.linalg.solve(A, astar[:, :, None])[:, :, 0]       # (f, run): weights of the four runs
	recip = float(np.max(np.abs(S - S.transpose(0, 2, 1))[(f > 2.3e9) & (f < 2.6e9)]))
	dB = 20 * np.log10(np.abs(gin))
	ble = (f >= 2.402e9) & (f <= 2.480e9)
	np.savez_compressed(os.path.join(a.out, 'matched.npz'), f=f, S=S, gin=gin, ploss=ploss, c=c, ZL=ZL)
	np.savetxt(os.path.join(a.out, 'S11_matched.csv'), np.column_stack([f, gin.real, gin.imag, dB,
		1 - np.abs(gin) ** 2 - ploss.sum(1)]), delimiter=',', comments='', fmt='%.6g',
		header='f_Hz,S11_re,S11_im,S11_dB,P_into_antenna_frac')
	out = {'runs': a.runs, 'parts': {'L2': a.L2, 'C1': a.C1, 'L1': a.L1, 'QL': a.QL, 'QC': a.QC, 'CP': a.CP, 'ESL': a.ESL},
		'reciprocity_max_abs_Sij_minus_Sji_2.3_2.6GHz': recip,
		'S11_matched_min_dB': float(dB.min()), 'f_min': float(f[np.argmin(dB)]),
		'ble_worst_dB': float(dB[ble].max()), 'ble_best_dB': float(dB[ble].min()), 'eff': []}

	# far field of the matched network: superposed face currents
	theta, phi = np.arange(0, 181, 5), np.arange(0, 361, 5)
	board = json.load(open(os.path.join(HERE, json.load(open(os.path.join(a.runs[0], 'case.json')))['board'])))
	o = np.array(board['outline'][0])
	zF = board['stackup']['copper']['F.Cu']['z']
	center = [(o[:, 0].min() + o[:, 0].max()) / 2, (o[:, 1].min() + o[:, 1].max()) / 2, zF / 2]
	Ds = []
	for k, fk in enumerate(NF2FF_F):
		j = int(np.argmin(np.abs(f - fk)))
		P = Wt = None
		J = M = 0
		for r, cr in zip(a.runs, c[j]):
			p, wt, Jr, Mr, _ = load_faces(os.path.join(r, 'sim'), fidx=k)
			P, Wt = p, wt
			J = J + cr * Jr
			M = M + cr * Mr
		Prad, D = far(P, Wt, J, M, fk, center, theta, phi)
		pinc = 0.5
		pl = ploss[j] / 2
		e = {'f': fk, 'S11_dB': float(dB[j]), 'mismatch_frac': float(np.abs(gin[j]) ** 2),
			'loss_L2': float(pl[0] / pinc), 'loss_C1': float(pl[1] / pinc), 'loss_L1': float(pl[2] / pinc),
			'into_antenna': float(1 - np.abs(gin[j]) ** 2 - ploss[j].sum()), 'tot_eff': Prad / pinc,
			'Dmax_dBi': float(D.max())}
		e['rad_eff_of_antenna'] = e['tot_eff'] / e['into_antenna']
		out['eff'].append(e)
		Ds.append(D)
		print('%.3f GHz: S11 %.2f dB, part loss L2 %.1f %% C1 %.1f %% L1 %.1f %%, into antenna %.1f %%, total eff %.1f %%, '
			'antenna rad eff %.1f %%, Dmax %.2f dBi' % (fk / 1e9, e['S11_dB'], 100 * e['loss_L2'], 100 * e['loss_C1'],
			100 * e['loss_L1'], 100 * e['into_antenna'], 100 * e['tot_eff'], 100 * e['rad_eff_of_antenna'], e['Dmax_dBi']), flush=True)
	np.savez_compressed(os.path.join(a.out, 'pattern.npz'), f=np.array(NF2FF_F), theta=theta, phi=phi, D_dBi=np.array(Ds))
	print('matched S11: min %.2f dB at %.3f GHz, BLE worst %.2f dB, best %.2f dB, reciprocity %.3g' % (
		out['S11_matched_min_dB'], out['f_min'] / 1e9, out['ble_worst_dB'], out['ble_best_dB'], recip), flush=True)

	# matched 2.44 GHz field dumps (same files as one run, fields replaced by the weighted sum)
	if not a.nofields:
		j = int(np.argmin(np.abs(f - FIELD_F[0])))
		out['field_weights_2440'] = [[float(x.real), float(x.imag)] for x in c[j]]
		for p in sorted(glob.glob(os.path.join(a.runs[0], 'sim', 'fd_*.h5'))):
			nm = os.path.basename(p)
			dst = os.path.join(a.out, nm)
			shutil.copyfile(p, dst)
			tot = 0
			for r, cr in zip(a.runs, c[j]):
				with h5py.File(os.path.join(r, 'sim', nm), 'r') as h:
					tot = tot + cr * np.array(h['FieldData/FD/f0']).astype(complex)
			with h5py.File(dst, 'r+') as h:
				ds = h['FieldData/FD/f0']
				if ds.dtype.names:                      # compound real / imag like openEMS writes
					v = np.empty(tot.shape, ds.dtype)
					v[ds.dtype.names[0]], v[ds.dtype.names[1]] = tot.real, tot.imag
					ds[...] = v
				else:
					attrs = dict(ds.attrs)
					del h['FieldData/FD/f0']
					nd = h['FieldData/FD'].create_dataset('f0', data=tot)
					for k2, v2 in attrs.items():
						nd.attrs[k2] = v2
			print('matched', nm, flush=True)
		for lg in ('run.log',):
			shutil.copyfile(os.path.join(a.runs[0], lg), os.path.join(a.out, lg))
	json.dump(out, open(os.path.join(a.out, 'matched.json'), 'w'), indent=1)


if __name__ == '__main__':
	main()

"""Near-to-far-field transform from openEMS frequency-domain box dumps (nf2ff_E_<n>.h5 / nf2ff_H_<n>.h5).

Independent of the openEMS C++ NF2FF code, which gives box-size dependent results for our board setups
(2026-11-03: Prad 30 % of the accepted power for a lossless 4-layer bench case, while the Poynting flux through
the same box was 109 %). Equivalent surface currents on the six faces (J = n x H, M = -n x E), radiation vectors
N and L, radiation intensity U (Balanis, ch. 12):
    U = k^2 / (32 pi^2 eta) (|L_phi + eta N_theta|^2 + |L_theta - eta N_phi|^2)

farfield(sim_dir, name, f, theta_deg, phi_deg) -> dict with Prad, U (theta x phi), D_dBi, Dmax_dBi, Poynting
"""
import h5py
import numpy as np

ETA0 = 376.730313668
C0 = 299792458.0


def _weights(c):
	if len(c) == 1:
		return np.ones(1)
	w = np.zeros(len(c))
	d = np.diff(c)
	w[:-1] += d / 2
	w[1:] += d / 2
	return w


def load_faces(sim_dir, name='nf2ff', fidx=0):
	"""Points (P, 3) in m, area weights (P,), J (P, 3), M (P, 3) and the face Poynting flux (W)."""
	pts, wts, Js, Ms = [], [], [], []
	flux = 0.0
	for n in range(6):
		fe = h5py.File('%s/%s_E_%d.h5' % (sim_dir, name, n), 'r')
		fh = h5py.File('%s/%s_H_%d.h5' % (sim_dir, name, n), 'r')
		x, y, z = (np.array(fe['Mesh'][k], float) for k in 'xyz')      # already in m (mesh_scaling attr not applied)
		E = np.array(fe['FieldData/FD/f%d' % fidx]).astype(complex)       # (3, nx, ny, nz)
		H = np.array(fh['FieldData/FD/f%d' % fidx]).astype(complex)
		ax = n // 2
		nv = np.zeros(3)
		nv[ax] = -1.0 if n % 2 == 0 else 1.0
		X, Y, Z = np.meshgrid(x, y, z, indexing='ij')
		W = np.einsum('i,j,k->ijk', *[(_weights(c) if i != ax else np.ones(len(c))) for i, c in enumerate((x, y, z))])
		P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
		Ev = E.reshape(3, -1).T
		Hv = H.reshape(3, -1).T
		J = np.cross(nv, Hv)
		M = -np.cross(nv, Ev)
		S = 0.5 * np.real(np.cross(Ev, np.conj(Hv)))
		flux += float(np.sum((S @ nv) * W.ravel()))
		pts.append(P)
		wts.append(W.ravel())
		Js.append(J)
		Ms.append(M)
	return np.vstack(pts), np.concatenate(wts), np.vstack(Js), np.vstack(Ms), flux


def farfield(sim_dir, f, theta_deg, phi_deg, center=(0, 0, 0), name='nf2ff', fidx=0, chunk=400):
	P, w, J, M, flux = load_faces(sim_dir, name, fidx)
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
		ph_ = np.exp(1j * k * (r[a:a + chunk] @ P.T))           # (d, P)
		N = ph_ @ Jw                                            # (d, 3)
		L = ph_ @ Mw
		Nt = np.sum(N * et[a:a + chunk], 1)
		Np = np.sum(N * ep[a:a + chunk], 1)
		Lt = np.sum(L * et[a:a + chunk], 1)
		Lp = np.sum(L * ep[a:a + chunk], 1)
		U[a:a + chunk] = k ** 2 / (32 * np.pi ** 2 * ETA0) * (np.abs(Lp + ETA0 * Nt) ** 2 + np.abs(Lt - ETA0 * Np) ** 2)
	U = U.reshape(TH.shape)
	# integrate over the sphere (trapezoid in theta and phi; phi grid should include 0 and 360)
	Prad = np.trapezoid(np.trapezoid(U * np.sin(TH), ph, axis=1), th)
	D = 4 * np.pi * U / Prad
	return {'Prad': float(Prad), 'U': U, 'D_dBi': 10 * np.log10(np.maximum(D, 1e-12)), 'Dmax_dBi': float(10 * np.log10(D.max())),
		'flux': flux, 'theta': np.asarray(theta_deg), 'phi': np.asarray(phi_deg)}


if __name__ == '__main__':
	import json
	import sys
	sim, rj = sys.argv[1], sys.argv[2]
	r = json.load(open(rj))
	ff = farfield(sim, 2.45e9, np.arange(0, 181, 3), np.arange(0, 361, 5))
	print('Prad_own %.4g  flux %.4g  P_acc %.4g  Prad_openEMS %.4g | own/P_acc %.3f  flux/P_acc %.3f  openEMS/P_acc %.3f | Dmax own %.2f dBi (openEMS %.2f)' % (
		ff['Prad'], ff['flux'], r['P_acc'], r['Prad_nf2ff'], ff['Prad'] / r['P_acc'], ff['flux'] / r['P_acc'], r['Prad_nf2ff'] / r['P_acc'],
		ff['Dmax_dBi'], r['Dmax_dBi_245']))

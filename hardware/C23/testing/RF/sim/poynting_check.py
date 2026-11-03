"""Power balance check from kept NF2FF frequency-domain dumps: integrates the Poynting vector over the six faces
of the NF2FF box and compares it with the accepted port power and the NF2FF radiated power.

Usage: python poynting_check.py <sim_dir> <case_result.json>
"""
import json
import sys

import h5py
import numpy as np

sim, rj = sys.argv[1], sys.argv[2]
r = json.load(open(rj))
tot = 0
for n in range(6):
	fe = h5py.File('%s/nf2ff_E_%d.h5' % (sim, n), 'r')
	fh = h5py.File('%s/nf2ff_H_%d.h5' % (sim, n), 'r')
	sc = fe['Mesh'].attrs.get('mesh_scaling', 1.0)
	x, y, z = (np.array(fe['Mesh'][k]) * sc for k in 'xyz')
	E = np.array(fe['FieldData/FD/f0'])
	H = np.array(fh['FieldData/FD/f0'])
	S = 0.5 * np.real(np.cross(E, np.conj(H), axis=0))     # (3, nx, ny, nz)
	ax = n // 2
	sign = -1 if n % 2 == 0 else 1
	Sn = sign * S[ax]
	coords = [x, y, z]
	others = [i for i in range(3) if i != ax]
	Sn = np.squeeze(Sn, axis=ax)
	P = np.trapezoid(np.trapezoid(Sn, coords[others[1]], axis=1), coords[others[0]], axis=0)
	print('face %d (axis %s, %s): %.4g W   grid %s' % (n, 'xyz'[ax], '-' if sign < 0 else '+', P, [len(c) for c in coords]))
	tot += P
print('Poynting total %.4g | P_acc %.4g | Prad_nf2ff %.4g | Poynting/P_acc %.3f | nf2ff/P_acc %.3f' % (
	tot, r['P_acc'], r['Prad_nf2ff'], tot / r['P_acc'], r['Prad_nf2ff'] / r['P_acc']))

"""Pick L2 / L3 / L4 parts from a 4-port board simulation (ports J2, L2, L3, L4; sim_board.py "multi").

Usage: python match.py <S4P.s4p> [--max-parts N] [--top K]

The L2 port sits across the L2 pad gap (series part), L3 and L4 from the signal pad to the GND pad (shunt
parts). Fitting a part = terminating that port with the part's impedance, so the 1-port S11 at J2 is
    G_in = S11 + S1x (G_L^-1 - Sxx)^-1 Sx1
with G_L the parts' reflection coefficients (open: +1, 0R: -1).

Part models (0402, approximate, no vendor S-parameters):
    inductor  Z = jwL + wL/Q, Q = 35 at 2.44 GHz (wire-wound LQW15 class), SRF ignored
    capacitor Z = 1/(jwC) + 0.25 ohm + jw 0.35 nH (C0G, ESL of the 0402 body)
Ranks by worst S11 over the BLE band. Part loss is in the S11 (lossy loads) but not reported separately.
"""
import argparse
import itertools

import numpy as np

BLE = (2.400e9, 2.4835e9)
L_E = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8,
	7.5, 8.2, 9.1, 10.0, 12.0, 15.0]
C_E = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6,
	3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 8.2, 10.0, 12.0, 15.0, 18.0, 22.0]
Q_L = 35.0


def read_s4p(path):
	vals = []
	for line in open(path):
		line = line.split('!')[0].strip()
		if not line or line.startswith('#'):
			continue
		vals += [float(v) for v in line.split()]
	vals = np.array(vals).reshape(-1, 33)
	f = vals[:, 0]
	ri = vals[:, 1:].reshape(-1, 16, 2)
	S = (ri[:, :, 0] + 1j * ri[:, :, 1]).reshape(-1, 4, 4)
	return f, S


def part_z(kind, v, f):
	w = 2 * np.pi * f
	if kind == 'L':
		L = v * 1e-9
		return 1j * w * L + 2 * np.pi * 2.44e9 * L / Q_L
	if kind == 'C':
		return 1 / (1j * w * v * 1e-12) + 0.25 + 1j * w * 0.35e-9
	raise ValueError(kind)


def options(slot):
	base = [('0R', None)] if slot == 'L2' else [('open', None)]
	return base + [('L', v) for v in L_E] + [('C', v) for v in C_E]


def gamma(opt, f):
	k, v = opt
	if k == 'open':
		return np.ones_like(f, complex)
	if k == '0R':
		return -np.ones_like(f, complex)
	Z = part_z(k, v, f)
	return (Z - 50) / (Z + 50)


def name(opt):
	k, v = opt
	return k if v is None else ('%gnH' % v if k == 'L' else '%gpF' % v)


def gin(S, G):
	# S: (nf,4,4), G: (nf,3) loads on ports 2..4
	S11 = S[:, 0, 0]
	S1x = S[:, 0, 1:]
	Sx1 = S[:, 1:, 0]
	Sxx = S[:, 1:, 1:]
	M = np.zeros_like(Sxx)
	for k in range(3):
		M[:, k, k] = 1 / G[:, k]
	inv = np.linalg.inv(M - Sxx)
	return S11 + np.einsum('fi,fij,fj->f', S1x, inv, Sx1)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('s4p')
	ap.add_argument('--max-parts', type=int, default=2)
	ap.add_argument('--top', type=int, default=12)
	a = ap.parse_args()
	f, S = read_s4p(a.s4p)
	sel = (f >= BLE[0] - 20e6) & (f <= BLE[1] + 20e6)
	fb, Sb = f[sel], S[sel]
	ble = (fb >= BLE[0]) & (fb <= BLE[1])
	opts = {s: options(s) for s in ('L2', 'L3', 'L4')}
	gam = {s: [gamma(o, fb) for o in opts[s]] for s in opts}
	res = []
	for i2, i3, i4 in itertools.product(range(len(opts['L2'])), range(len(opts['L3'])), range(len(opts['L4']))):
		n = (i2 > 0) + (i3 > 0) + (i4 > 0)
		if n > a.max_parts:
			continue
		G = np.stack([gam['L2'][i2], gam['L3'][i3], gam['L4'][i4]], axis=1)
		g = gin(Sb, G)
		dB = 20 * np.log10(np.abs(g[ble]))
		res.append((dB.max(), dB.min(), n, (opts['L2'][i2], opts['L3'][i3], opts['L4'][i4])))
	res.sort(key=lambda r: r[0])
	print('S11 at J2 over the BLE band with fitted parts (L2 series, L3 shunt at J2, L4 shunt at the feed)')
	print('%-10s %-10s %-10s %10s %10s' % ('L2', 'L3', 'L4', 'worst dB', 'best dB'))
	none = [r for r in res if r[2] == 0][0]
	print('%-10s %-10s %-10s %10.2f %10.2f   (as simulated, no parts)' % ('0R', 'open', 'open', none[0], none[1]))
	for worst, best, n, o in res[:a.top]:
		print('%-10s %-10s %-10s %10.2f %10.2f' % (name(o[0]), name(o[1]), name(o[2]), worst, best))


if __name__ == '__main__':
	main()

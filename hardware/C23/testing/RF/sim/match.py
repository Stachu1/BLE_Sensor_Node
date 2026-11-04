"""Pick matching parts from a multi-port board simulation (sim_board.py "multi": J2 plus the part pads).

Usage: python match.py <S<n>P.s<n>p> [--max-parts N] [--top K]

Port names come from the file header (b1: J2 L2 L3 L4, b2: J2 L2 L3 since the antenna-side L4 was removed. The ref L4 is now the 10 uH DC-DC
inductor).

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
	names = None
	vals = []
	for line in open(path):
		if line.startswith('!') and 'ports' in line:
			names = line.split('ports', 1)[1].split()
		line = line.split('!')[0].strip()
		if not line or line.startswith('#'):
			continue
		vals += [float(v) for v in line.split()]
	n = len(names) if names else 4
	vals = np.array(vals).reshape(-1, 1 + 2 * n * n)
	f = vals[:, 0]
	ri = vals[:, 1:].reshape(-1, n * n, 2)
	S = (ri[:, :, 0] + 1j * ri[:, :, 1]).reshape(-1, n, n)
	return f, S, names or ['J2', 'L2', 'L3', 'L4']


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
	# S: (nf,n,n), G: (nf,n-1) loads on ports 2..n
	S11 = S[:, 0, 0]
	S1x = S[:, 0, 1:]
	Sx1 = S[:, 1:, 0]
	Sxx = S[:, 1:, 1:]
	M = np.zeros_like(Sxx)
	for k in range(G.shape[1]):
		M[:, k, k] = 1 / G[:, k]
	inv = np.linalg.inv(M - Sxx)
	return S11 + np.einsum('fi,fij,fj->f', S1x, inv, Sx1)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('s4p')
	ap.add_argument('--max-parts', type=int, default=2)
	ap.add_argument('--top', type=int, default=12)
	a = ap.parse_args()
	f, S, names = read_s4p(a.s4p)
	slots = names[1:]
	sel = (f >= BLE[0] - 20e6) & (f <= BLE[1] + 20e6)
	fb, Sb = f[sel], S[sel]
	ble = (fb >= BLE[0]) & (fb <= BLE[1])
	opts = {s: options(s) for s in slots}
	gam = {s: [gamma(o, fb) for o in opts[s]] for s in opts}
	res = []
	for idx in itertools.product(*[range(len(opts[s])) for s in slots]):
		n = sum(i > 0 for i in idx)
		if n > a.max_parts:
			continue
		G = np.stack([gam[s][i] for s, i in zip(slots, idx)], axis=1)
		g = gin(Sb, G)
		dB = 20 * np.log10(np.abs(g[ble]))
		res.append((dB.max(), dB.min(), n, tuple(opts[s][i] for s, i in zip(slots, idx))))
	res.sort(key=lambda r: r[0])
	print('S11 at J2 over the BLE band with fitted parts (L2 series, the others shunt). Part models in the docstring.')
	print(' '.join('%-10s' % s for s in slots) + ' %10s %10s' % ('worst dB', 'best dB'))
	none = [r for r in res if r[2] == 0][0]
	print(' '.join('%-10s' % name(o) for o in none[3]) + ' %10.2f %10.2f   (as simulated, no parts)' % (none[0], none[1]))
	for worst, best, n, o in res[:a.top]:
		print(' '.join('%-10s' % name(x) for x in o) + ' %10.2f %10.2f' % (worst, best))


if __name__ == '__main__':
	main()

"""Parts for the BSN-N52 RF network: radio ANT (50 ohm assumed) -> L2 series -> C1 shunt -> L1 series -> antenna.

The board has this low-pass T (Nordic reference values L2 2.2 nH, C1 1.2 pF, L1 3.3 nH, made for 0201 parts). The
antenna sims put the port beside the L1 pad on the antenna side, so the simulated Zin is exactly the load of L1.
This script searches L2, C1, L1 over real 0402 values (or a 0.1 nH grid) with lossy parts and scores the worst BLE
channel, either by the power that reaches the antenna (default, mismatch + part loss) or by S11:

    inductors   series R = wL / Q_L, parallel self capacitance C_P (SRF)
    capacitors  series R = 1 / (wC Q_C), series ESL
    mask        the simulated antenna frequencies are divided by --shift (solder mask, 0.73 % measured on r1)

Prints, per run: no parts, Nordic values, best T. For the best T: worst BLE S11, the power delivered to the antenna
(mismatch and part loss), and the harmonic rejection of the network between 50 ohm and 50 ohm at 2f and 3f
(the antenna impedance at the harmonics is not simulated, so this is the filter alone).

Usage: python match_tee.py [--shift 1.0073] [--QL 50] [--QC 100] [--grid parts|fine] [--score power|s11] hash ...     (runs in results/runs)
"""
import argparse
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BLE = (2.402e9, 2.480e9)
Z0 = 50.0


E_L = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8,
	7.5, 8.2, 8.7, 9.1, 10, 11, 12, 13, 15, 16, 18, 20, 22, 24, 27]   # nH, LQW15AN series (check stock before ordering)


def ind(L, w, QL, CP):
	"""Impedance of a real inductor (L in H) at w (arrays broadcast)."""
	L = np.where(L > 0, L, 1e-15)
	zl = 1j * w * L + w * L / QL
	if CP:
		zl = 1 / (1 / zl + 1j * w * CP)
	with np.errstate(divide='ignore', invalid='ignore'):
		return np.where(L > 0, zl, 1e-3)      # L 0 = 0 ohm link


def cap(C, w, QC, ESL):
	return 1 / (1j * w * C) + 1 / (w * C * QC) + 1j * w * ESL


def tee_abcd(L2, C1, L1, w, a):
	"""ABCD of series L2, shunt C1, series L1 (source side first)."""
	z2 = ind(L2, w, a.QL, a.CP)
	z1 = ind(L1, w, a.QL, a.CP)
	y = 1 / cap(C1, w, a.QC, a.ESL)
	A = 1 + z2 * y
	B = z2 + z1 + z2 * z1 * y
	C = y
	D = 1 + z1 * y
	return A, B, C, D


def zin(L2, C1, L1, w, ZL, a):
	A, B, C, D = tee_abcd(L2, C1, L1, w, a)
	return (A * ZL + B) / (C * ZL + D), (A, B, C, D)


def delivered(A, B, C, D, ZL):
	"""Fraction of the available source power that reaches ZL (mismatch + part loss)."""
	V2 = ZL / (A * ZL + B + Z0 * (C * ZL + D))     # V2 / Vs
	Pl = np.abs(V2) ** 2 * np.real(1 / ZL)
	return Pl / (1 / (4 * Z0))


def s21_50(L2, C1, L1, f, a):
	w = 2 * np.pi * f
	A, B, C, D = tee_abcd(np.asarray(L2), np.asarray(C1), np.asarray(L1), w, a)
	return 20 * np.log10(np.abs(2 / (A + B / Z0 + C * Z0 + D)))


def load(h, shift):
	d = np.genfromtxt(os.path.join(HERE, 'results', 'runs', h, 'S11.csv'), delimiter=',', names=True)
	f = d['f_Hz'] / shift
	Z = d['Zin_re_ohm'] + 1j * d['Zin_im_ohm']
	fb = np.linspace(BLE[0], BLE[1], 40)
	return fb, np.interp(fb, f, Z.real) + 1j * np.interp(fb, f, Z.imag), f, Z


def s11db(Z):
	return 20 * np.log10(np.abs((Z - Z0) / (Z + Z0)))


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('hashes', nargs='+')
	ap.add_argument('--shift', type=float, default=1.0073)
	ap.add_argument('--QL', type=float, default=50.0, help='inductor Q at 2.44 GHz (LQW15AN typ. 40-70)')
	ap.add_argument('--QC', type=float, default=100.0)
	ap.add_argument('--CP', type=float, default=0.08e-12, help='inductor self capacitance (F)')
	ap.add_argument('--ESL', type=float, default=0.3e-9, help='capacitor ESL (H)')
	ap.add_argument('--json', help='write the results here')
	ap.add_argument('--min-rej', type=float, default=20.0, help='required rejection of 2f and 3f relative to f (dB)')
	ap.add_argument('--grid', choices=('parts', 'fine'), default='parts', help='parts: real inductor values, fine: 0.1 nH')
	ap.add_argument('--score', choices=('power', 's11'), default='power',
		help='power: maximise the worst-channel power into the antenna (mismatch + part loss), s11: worst S11')
	a = ap.parse_args()

	if a.grid == 'fine':
		Ls = np.round(np.arange(0.0, 20.01, 0.1), 2) * 1e-9
	else:                                      # 0 ohm + Murata LQW15AN (0402 wire-wound) values
		Ls = np.array([0] + E_L) * 1e-9
	Cs = np.round(np.arange(0.1, 4.01, 0.1), 2) * 1e-12          # 0402 C0G in 0.1 pF steps (GJM15 range)
	L2g, C1g, L1g = np.meshgrid(Ls, Cs, Ls, indexing='ij')
	out = []
	for h in a.hashes:
		fb, ZL, f, Zall = load(h, a.shift)
		name = json.load(open(os.path.join(HERE, 'results', 'runs', h, 'case.json'))).get('name', h)
		w = 2 * np.pi * fb
		worst = np.full(L2g.shape, -1e9)
		for wi, zl in zip(w, ZL):              # worst BLE value over the grid, one frequency at a time
			z, abcd = zin(L2g, C1g, L1g, wi, zl, a)
			v = s11db(z) if a.score == 's11' else -10 * np.log10(delivered(*abcd, zl))
			np.maximum(worst, v, out=worst)
		if a.min_rej > 0:                       # keep only networks that still filter the harmonics (50 / 50 ohm)
			ref = s21_50(L2g, C1g, L1g, 2.44e9, a)
			for k in (2, 3):
				worst[ref - s21_50(L2g, C1g, L1g, k * 2.44e9, a) < a.min_rej] = 1e9
		i = np.unravel_index(np.argmin(worst), worst.shape)
		best = (L2g[i], C1g[i], L1g[i])
		nord = (2.2e-9, 1.2e-12, 3.3e-9)
		res = {'run': h, 'name': name, 'none': float(s11db(ZL).max())}
		for key, (L2, C1, L1) in (('nordic', nord), ('best', best)):
			z, abcd = zin(L2, C1, L1, w, ZL, a)
			p = delivered(*abcd, ZL)
			s21 = s21_50(L2, C1, L1, np.array([2.44e9, 4.88e9, 7.32e9]), a)
			res[key] = {'L2_nH': round(L2 * 1e9, 2), 'C1_pF': round(C1 * 1e12, 2), 'L1_nH': round(L1 * 1e9, 2),
				'worst_S11_dB': round(float(s11db(z).max()), 2), 'min_delivered_dB': round(float(10 * np.log10(p.min())), 2),
				'harm_rej_2f_dB': round(float(s21[0] - s21[1]), 1), 'harm_rej_3f_dB': round(float(s21[0] - s21[2]), 1)}
		out.append(res)
		b, n = res['best'], res['nordic']
		print('%s  %-36s none %6.1f | Nordic %6.1f dB | best L2 %4.1f nH C1 %4.1f pF L1 %4.1f nH: %6.1f dB, '
			'delivered >= %5.2f dB, 2f -%4.1f dB, 3f -%4.1f dB' % (h, name[:36], res['none'], n['worst_S11_dB'],
			b['L2_nH'], b['C1_pF'], b['L1_nH'], b['worst_S11_dB'], b['min_delivered_dB'], b['harm_rej_2f_dB'], b['harm_rej_3f_dB']))
	if a.json:
		json.dump(out, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
	main()

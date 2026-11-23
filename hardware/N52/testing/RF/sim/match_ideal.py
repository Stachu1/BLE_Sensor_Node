"""Quick matching estimate: ideal (lossless) parts placed right at the antenna port (BSN-N52: the feed notch).

For each run it prints the worst S11 over BLE with no parts, with the best single part (shunt or series C / L),
and with the best two-part L network in either orientation:
    series at the antenna, then shunt on the 50 ohm side   (for antennas with R below 50 ohm)
    shunt at the antenna, then series toward 50 ohm         (for antennas with R above 50 ohm, typical of the MIFA)
Parts are listed from the antenna toward the chip. This ignores the trace to the pads and the part losses, so
it is optimistic (BSN: ideal -15.3 dB became -10.9 dB with real pads and parts).
(Copied from the BLE_Sensor_Node pipeline, 2026-11-14 the shunt-first orientation was added for the BSN-N52 MIFA.)

Usage: python match_ideal.py <runs_dir> [hash ...] [--shift 1.01]   (default: every single-port run in runs_dir)
    --shift k  divide the simulated frequencies by k before scoring: the solder mask (not in the model) moves the
               curve down by about 1 %, and the tuners aim 1 % high (2.465 GHz), so --shift 1.01 scores the
               expected real-board curve.
"""
import glob
import json
import os
import sys

import numpy as np

BLE = (2.400e9, 2.4835e9)
SHIFT = 1.0


def apply(Z, f, net):
	"""net: list of (kind, value) from the antenna toward J2. kind: sL (nH), sC (pF), pL (nH), pC (pF)."""
	w = 2 * np.pi * f
	for kind, v in net:
		if kind == 'sL':
			Z = Z + 1j * w * v * 1e-9
		elif kind == 'sC':
			Z = Z + 1 / (1j * w * v * 1e-12)
		elif kind == 'pL':
			Z = 1 / (1 / Z + 1 / (1j * w * v * 1e-9))
		elif kind == 'pC':
			Z = 1 / (1 / Z + 1j * w * v * 1e-12)
	return Z


def describe(net):
	if not net:
		return 'no parts'
	names = {'sL': 'series %.2f nH', 'sC': 'series %.2f pF', 'pL': 'shunt %.2f nH', 'pC': 'shunt %.2f pF'}
	return ', '.join(names[k] % v for k, v in net)


def analyse(d=None, f=None, Z=None):
	if d is not None:
		a = np.loadtxt(os.path.join(d, 'S11.csv'), delimiter=',', skiprows=1)
		f, Z = a[:, 0] / SHIFT, a[:, 4] + 1j * a[:, 5]
	m = (f >= BLE[0]) & (f <= BLE[1])
	fm, Zm = f[m], Z[m]

	def worst(net):
		z = apply(Zm, fm, net)
		return float(20 * np.log10(np.max(np.abs((z - 50) / (z + 50)))))

	shunts = [('pC', v) for v in np.arange(0.05, 6, 0.05)] + [('pL', v) for v in np.arange(0.5, 40, 0.25)]
	series = [('sL', v) for v in np.arange(0.2, 15, 0.2)] + [('sC', v) for v in np.arange(0.3, 10, 0.1)]
	one = min((worst([s]), [s]) for s in shunts + series)
	two = min([(worst([s, p]), [s, p]) for s in series for p in shunts[::2]] +
		[(worst([p, s]), [p, s]) for p in shunts[::2] for s in series] + [one])
	# refine the two-part result on a fine grid around the best values
	if len(two[1]) == 2:
		(k1, v1), (k2, v2) = two[1]
		two = min([two] + [(worst([(k1, a), (k2, b)]), [(k1, a), (k2, b)])
			for a in np.linspace(v1 * 0.9, v1 * 1.1, 21) if a > 0 for b in np.linspace(v2 * 0.9, v2 * 1.1, 21) if b > 0])
	k = int(np.argmin(np.abs(f - 2.44e9)))
	kr = int(np.argmin(np.abs((Z - 50) / (Z + 50))))
	return {'none': worst([]), 'one': one, 'two': two, 'Z2440': Z[k], 'f_min': f[kr], 'f': f, 'Z': Z}


def main():
	global SHIFT
	argv = sys.argv[1:]
	if '--shift' in argv:
		i = argv.index('--shift')
		SHIFT = float(argv[i + 1])
		del argv[i:i + 2]
	root = argv[0]
	hs = argv[1:] or [os.path.basename(os.path.dirname(p)) for p in sorted(glob.glob(os.path.join(root, '*', 'S11.csv')))]
	for h in hs:
		d = os.path.join(root, h)
		cp = os.path.join(d, 'case.json')
		c = json.load(open(cp)) if os.path.exists(cp) else json.load(open(os.path.join(d, 'result.json')))['case']
		if c.get('ports', 'j2') not in ('j2', 'feed') or not os.path.exists(os.path.join(d, 'S11.csv')):
			continue
		r = analyse(d)
		print('%s %-55s Z(2.44) %5.1f%+6.1fj | none %5.1f | 1 part %5.1f (%s) | 2 parts %5.1f (%s)' % (
			h, c.get('name', '')[:55], r['Z2440'].real, r['Z2440'].imag, r['none'], r['one'][0], describe(r['one'][1]),
			r['two'][0], describe(r['two'][1])))


if __name__ == '__main__':
	main()

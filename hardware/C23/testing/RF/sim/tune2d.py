"""Tune two antenna parameters so that Zin at J2 is 50 + 0j ohm at the target frequency (server).

Usage: nohup python tune2d.py <config.json> > opt/<name>.log 2>&1 &
config.json:
    name, family, start {params}, vars [p1, p2], deltas [d1, d2] (finite-difference steps, mm),
    ranges {p: [lo, hi]}, target (Hz), max_iter, threads, case {extra case keys}
Method: finite-difference Jacobian of (R, X) at the target over the two variables (3 runs), then damped
Newton steps with Broyden updates (1 run per step). Steps are limited to max_step mm and clipped to the
ranges and to the geometry rules (antenna.check). Stops when |S11| at the target < stop_db (default -25 dB)
or after max_iter steps. Writes opt/<name>.json with every evaluated design.
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import antenna as ant  # noqa: E402
from runner import run_cases  # noqa: E402

cfg = json.load(open(sys.argv[1]))
NAME, FAM = cfg['name'], cfg['family']
V = cfg['vars']
D = cfg['deltas']
FT = cfg.get('target', 2.45e9)
RANGES = cfg.get('ranges', {})
MAXSTEP = cfg.get('max_step', 2.0)
STOP = cfg.get('stop_db', -25.0)
THR = cfg.get('threads', 6)
EXTRA = cfg.get('case', {})
GRID = 0.05
OUT = os.path.join(HERE, 'opt')
os.makedirs(OUT, exist_ok=True)
t0 = time.time()
history = []


def log(m):
	print('[%6.1f min] %s' % ((time.time() - t0) / 60, m), flush=True)


def mk(base, x):
	p = dict(base, family=FAM)
	for k, v in zip(V, x):
		v = round(round(v / GRID) * GRID, 4)
		if k in RANGES:
			v = min(max(v, RANGES[k][0]), RANGES[k][1])
		p[k] = v
	return p


def zt(r):
	d = np.loadtxt(os.path.join(HERE, 'runs', r['hash'], 'S11.csv'), delimiter=',', skiprows=1)
	k = int(np.argmin(np.abs(d[:, 0] - FT)))
	return complex(d[k, 4], d[k, 5])


def evaluate(ps):
	res = run_cases([dict(EXTRA, antenna=p) for p in ps], parallel=len(ps), threads=THR, tag='tune_' + NAME,
		names=['%s %s' % (NAME, ant.describe(p)) for p in ps])
	out = []
	for p, r in zip(ps, res):
		if 'metrics' not in r:
			log('FAILED %s %s' % (ant.describe(p), r.get('error')))
			out.append(None)
			continue
		z = zt(r)
		g = (z - 50) / (z + 50)
		m = r['metrics']
		eff = np.mean([e['rad_eff'] for e in r['eff']]) if r.get('eff') else float('nan')
		h = {'params': p, 'hash': r['hash'], 'Z': [z.real, z.imag], 's_target': 20 * np.log10(abs(g)),
			'metrics': m, 'eff': r.get('eff')}
		history.append(h)
		out.append(h)
		log('%s %-60s Z(%.3f) %6.1f%+6.1fj  S11 %6.1f dB | min %6.1f @ %.3f | BLE worst %6.1f | bw10 %s | eff %.2f' % (
			r['hash'], ant.describe(p), FT / 1e9, z.real, z.imag, h['s_target'], m['s_min'], m['f_min'] / 1e9,
			m['ble_worst'], m['bw10'] and '%.0f MHz' % ((m['bw10'][1] - m['bw10'][0]) / 1e6), eff))
	json.dump({'cfg': cfg, 'history': history}, open(os.path.join(OUT, NAME + '.json'), 'w'), indent=1)
	return out


def valid_step(base, x, dx):
	"""Shrink the step until the design passes antenna.check (e.g. the arm reaching the corner)."""
	for s in (1, 0.5, 0.25, 0.1):
		p = mk(base, x + s * dx)
		if not ant.check(p):
			return p, x + s * dx
	return None, None


def main():
	log('config %s' % json.dumps(cfg))
	base = dict(cfg['start'])
	x = np.array([base[k] for k in V], float)
	p0 = mk(base, x)
	if ant.check(p0):
		sys.exit('start invalid: %s' % ant.check(p0))
	ps = [p0] + [mk(base, x + np.eye(2)[i] * D[i]) for i in range(2)]
	ok = [not ant.check(p) for p in ps]
	for i in (1, 2):
		if not ok[i]:
			ps[i] = mk(base, x - np.eye(2)[i] * D[i])
	hs = evaluate(ps)
	if any(h is None for h in hs):
		sys.exit('initial runs failed')
	F0 = np.array(hs[0]['Z'])
	J = np.zeros((2, 2))
	for i in range(2):
		dx = ps[i + 1][V[i]] - ps[0][V[i]]
		J[:, i] = (np.array(hs[i + 1]['Z']) - F0) / dx
	best = min(hs, key=lambda h: h['s_target'])
	x = np.array([best['params'][k] for k in V], float)
	Fx = np.array(best['Z'])
	for it in range(cfg.get('max_iter', 6)):
		if best['s_target'] < STOP:
			log('stop: S11 at target below %.0f dB' % STOP)
			break
		try:
			dx = np.linalg.solve(J, np.array([50.0, 0.0]) - Fx)
		except np.linalg.LinAlgError:
			log('singular Jacobian')
			break
		n = np.max(np.abs(dx))
		if n > MAXSTEP:
			dx *= MAXSTEP / n
		p, xn = valid_step(base, x, dx)
		if p is None:
			log('no valid step from %s along %s' % (x, dx))
			break
		xn = np.array([p[k] for k in V], float)
		if np.allclose(xn, x):
			log('step below the grid, done')
			break
		h = evaluate([p])[0]
		if h is None:
			break
		Fn = np.array(h['Z'])
		s = xn - x
		J = J + np.outer((Fn - Fx) - J @ s, s) / (s @ s)       # Broyden update
		x, Fx = xn, Fn                                       # Newton always moves on, best is kept separately
		if h['s_target'] < best['s_target']:
			best = h
	json.dump({'cfg': cfg, 'history': history, 'best': best}, open(os.path.join(OUT, NAME + '.json'), 'w'), indent=1)
	log('BEST %s %s S11(target) %.1f dB' % (best['hash'], ant.describe(best['params']), best['s_target']))


if __name__ == '__main__':
	main()

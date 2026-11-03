"""Compass-search tuning of one antenna family on the real board (server).

Usage: nohup python optimize.py <config.json> > opt_<name>.log 2>&1 &
config.json:
    name        label (results in opt/<name>.json)
    family      ifa | fifa
    start       start parameters (antenna.py)
    steps       {"S": 0.5, "L": 1.0, "H": 0.5, ...} initial compass steps of the tuned variables
    ranges      {"H": [lo, hi], ...} optional limits
    centre      target centre frequency in the simulation (Hz). The solder mask is not in the loop model,
                so this is the real target plus the mask shift.
    half_band   goal band = centre +- half_band (Hz)
    budget_h, parallel, threads
    case        extra case keys (battery, mesh, ...)
Objective (lower is better): worst S11 (dB) at J2 over the goal band, tie-break by mean radiation efficiency.
Each batch: a frequency-corrected centre point (L moved to put the match on the centre, slope fitted from
all runs) plus its compass neighbours. Steps halve when a batch does not improve. Stops at convergence,
at the budget, or when the objective is below `stop_db` (default -15 dB).
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

GRID = 0.1

cfg = json.load(open(sys.argv[1]))
NAME = cfg['name']
FAM = cfg['family']
CENTRE = cfg.get('centre', 2.45e9)
HALF = cfg.get('half_band', 70e6)
BUDGET = cfg.get('budget_h', 4) * 3600
PAR = cfg.get('parallel', 4)
THR = cfg.get('threads', 5)
STOP = cfg.get('stop_db', -15.0)
RANGES = cfg.get('ranges', {})
EXTRA = cfg.get('case', {})
OUT = os.path.join(HERE, 'opt')
os.makedirs(OUT, exist_ok=True)
t_start = time.time()
history = []


def log(msg):
	print('[%6.1f min] %s' % ((time.time() - t_start) / 60, msg), flush=True)


def snap(p):
	q = dict(p)
	for k, v in q.items():
		if k != 'family':
			q[k] = round(round(v / GRID) * GRID, 4)
			if k in RANGES:
				q[k] = min(max(q[k], RANGES[k][0]), RANGES[k][1])
	return q


def key(p):
	return json.dumps(p, sort_keys=True)


def objective(r):
	d = np.loadtxt(os.path.join(HERE, 'runs', r['hash'], 'S11.csv'), delimiter=',', skiprows=1)
	f, dB = d[:, 0], d[:, 3]
	sel = (f >= CENTRE - HALF) & (f <= CENTRE + HALF)
	eff = np.mean([e['rad_eff'] for e in r['eff']]) if r.get('eff') else 0
	return float(dB[sel].max()), float(eff)


def evaluate(ps):
	ps = [p for p in ps if not ant.check(p)]
	if not ps:
		return []
	res = run_cases([dict(EXTRA, antenna=p) for p in ps], PAR, THR, tag='opt_' + NAME,
		names=['%s %s' % (NAME, ant.describe(p)) for p in ps])
	out = []
	for p, r in zip(ps, res):
		if 'metrics' not in r:
			log('FAILED %s %s' % (ant.describe(p), r.get('error')))
			continue
		obj, eff = objective(r)
		h = {'params': p, 'hash': r['hash'], 'metrics': r['metrics'], 'eff': r.get('eff'), 'obj': obj, 'eff_mean': eff}
		history.append(h)
		out.append(h)
		m = r['metrics']
		log('%s %-55s obj %6.2f | min %6.2f dB @ %.3f GHz | Rmax %4.0f @ %.3f | eff %.2f' % (
			r['hash'], ant.describe(p), obj, m['s_min'], m['f_min'] / 1e9, m['Rmax'], m['f_Rmax'] / 1e9, eff))
	json.dump({'cfg': cfg, 'history': history}, open(os.path.join(OUT, NAME + '.json'), 'w'), indent=1)
	return out


def slope():
	if len(history) >= 4:
		A = np.array([[1, h['params']['L']] + [h['params'][k] for k in cfg['steps'] if k != 'L'] for h in history])
		y = np.array([track(h) for h in history])
		coef, *_ = np.linalg.lstsq(A, y, rcond=None)
		if -300e6 < coef[1] < -15e6:
			return coef[1]
	return cfg.get('slope0', -70e6)


def offset():
	offs = [h['metrics']['f_min'] - h['metrics']['f_Rmax'] for h in history
		if h['metrics']['min_interior'] and h['metrics']['s_min'] < -6]
	return float(np.median(offs[-6:])) if offs else 0.25e9


def track(h):
	m = h['metrics']
	return m['f_min'] if (m['min_interior'] and m['s_min'] < -6) else m['f_Rmax'] + offset()


def corrected(h):
	p = dict(h['params'])
	p['L'] += (CENTRE - track(h)) / slope()
	return snap(p)


def better(a, b):
	return (a['obj'], -a['eff_mean']) < (b['obj'] - 0.05, -b['eff_mean'])


def main():
	log('config %s' % json.dumps(cfg))
	start = snap(dict(cfg['start'], family=FAM))
	res = evaluate([start])
	if not res:
		sys.exit('start design failed: %s' % ant.check(start))
	best = res[0]
	steps = dict(cfg['steps'])
	seen = {key(start)}
	bt = None
	while True:
		if best['obj'] <= STOP:
			log('stop: objective below %.1f dB' % STOP)
			break
		if bt and time.time() - t_start + bt > BUDGET:
			log('time budget reached')
			break
		base = corrected(best)
		cands = [base]
		for k in steps:
			for sgn in (-1, 1):
				q = dict(base)
				q[k] += sgn * steps[k]
				if k == 'H':
					q['L'] -= sgn * steps[k]
				cands.append(snap(q))
		batch = []
		for q in cands:
			if key(q) not in seen and not ant.check(q):
				batch.append(q)
				seen.add(key(q))
		if not batch:
			if all(v <= GRID * 2 + 1e-9 for v in steps.values()):
				log('converged')
				break
			steps = {k: max(v / 2, GRID * 2) for k, v in steps.items()}
			continue
		t0 = time.time()
		res = evaluate(batch)
		bt = time.time() - t0
		cand = min(res, key=lambda h: (h['obj'], -h['eff_mean'])) if res else None
		if cand and better(cand, best):
			best = cand
			log('new best %s obj %.2f (steps %s)' % (ant.describe(best['params']), best['obj'], steps))
		else:
			if all(v <= GRID * 2 + 1e-9 for v in steps.values()):
				log('converged at the minimum step')
				break
			steps = {k: max(v / 2, GRID * 2) for k, v in steps.items()}
			log('no improvement, steps -> %s' % steps)
	json.dump({'cfg': cfg, 'history': history, 'best': best}, open(os.path.join(OUT, NAME + '.json'), 'w'), indent=1)
	log('BEST %s obj %.2f eff %.2f hash %s' % (ant.describe(best['params']), best['obj'], best['eff_mean'], best['hash']))


if __name__ == '__main__':
	main()

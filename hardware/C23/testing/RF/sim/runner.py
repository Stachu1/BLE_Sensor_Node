"""Run sim_board.py cases in parallel on the server, with a result cache keyed by the case content.

Library:  results = run_cases([case, ...], parallel=4, threads=5, tag='opt_ifa')
CLI:      python runner.py cases.json [parallel] [threads]     (cases.json: list of {"name", "purpose", "case"})
          "purpose" says why the run was made. It goes to case.json and index.jsonl, not into the cache key.

Each case runs in runs/<hash>/ (case.json, run.log, result.json, S11.csv). A case that already has a
result.json is not re-run. runs/index.jsonl gets one line per finished run (hash, name, tag, metrics).
"""
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, 'runs')
PY = sys.executable
DEFAULT_BOARD = 'build/board.json'
MODEL = 'v5'          # bump when sim_board.py changes the model, so cached results are not reused (v5: own far field)


def case_hash(case):
	s = json.dumps(case, sort_keys=True)
	return hashlib.sha1(s.encode()).hexdigest()[:10]


def normalise(case):
	c = {'model': MODEL, 'board': DEFAULT_BOARD, 'ports': 'j2', 'battery': True, 'mask': 'none', 'er_scale': 1.0, 'nf2ff': True}
	c.update(case)
	if isinstance(c['antenna'], dict):
		c['antenna'] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in c['antenna'].items()}
	return c


def load(h):
	p = os.path.join(RUNS, h, 'result.json')
	if os.path.exists(p):
		try:
			return json.load(open(p))
		except Exception:
			return None
	return None


def run_cases(cases, parallel=4, threads=5, tag='', names=None, purposes=None):
	os.makedirs(RUNS, exist_ok=True)
	cases = [normalise(c) for c in cases]
	hashes = [case_hash(c) for c in cases]
	names = names or [''] * len(cases)
	purposes = purposes or [''] * len(cases)
	results = [load(h) for h in hashes]
	todo = [k for k, r in enumerate(results) if r is None]
	running = []
	while todo or running:
		while todo and len(running) < parallel:
			k = todo.pop(0)
			d = os.path.join(RUNS, hashes[k])
			os.makedirs(d, exist_ok=True)
			with open(os.path.join(d, 'case.json'), 'w') as fh:
				json.dump(dict(cases[k], name=names[k], tag=tag, purpose=purposes[k]), fh, indent=1)
			proc = subprocess.Popen([PY, '-u', os.path.join(HERE, 'sim_board.py'), d, str(threads)],
				stdout=open(os.path.join(d, 'run.log'), 'w'), stderr=subprocess.STDOUT, cwd=HERE)
			running.append((k, proc, time.time()))
		time.sleep(5)
		for item in list(running):
			k, proc, t0 = item
			if proc.poll() is None:
				continue
			running.remove(item)
			r = load(hashes[k])
			results[k] = r
			with open(os.path.join(RUNS, 'index.jsonl'), 'a') as fh:
				fh.write(json.dumps({'hash': hashes[k], 'name': names[k], 'tag': tag, 'purpose': purposes[k], 'time': time.time(),
					'dt': time.time() - t0, 'ok': bool(r and 'metrics' in r),
					'metrics': r.get('metrics') if r else None, 'eff': r.get('eff') if r else None,
					'case': cases[k]}) + '\n')
	return [dict(r or {}, hash=h) for r, h in zip(results, hashes)]


if __name__ == '__main__':
	lst = json.load(open(sys.argv[1]))
	par = int(sys.argv[2]) if len(sys.argv) > 2 else 4
	thr = int(sys.argv[3]) if len(sys.argv) > 3 else 5
	tag = os.path.splitext(os.path.basename(sys.argv[1]))[0]
	res = run_cases([x['case'] for x in lst], par, thr, tag, [x.get('name', '') for x in lst],
		[x.get('purpose', '') for x in lst])
	for x, r in zip(lst, res):
		m = r.get('metrics')
		if m:
			print('%-28s %s  min %6.2f dB @ %.3f GHz  BLE worst %6.2f  Z %.1f%+.1fj  eff %s' % (
				x.get('name', ''), r['hash'], m['s_min'], m['f_min'] / 1e9, m['ble_worst'], *m['Z_2440'],
				[round(e['rad_eff'], 3) for e in r['eff']] if r.get('eff') else '-'))
		else:
			print('%-28s %s  FAILED %s' % (x.get('name', ''), r['hash'], r.get('error')))

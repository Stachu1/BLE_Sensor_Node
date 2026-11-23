"""Run sim_board.py cases in parallel on the server, with a result cache keyed by the case content.

Library:  results = run_cases([case, ...], parallel=4, threads=5, tag='x')
CLI:      python runner.py cases.json [parallel] [threads]     (cases.json: list of {"name", "purpose", "case"})
          "purpose" says why the run was made. It goes to case.json and index.jsonl, not into the cache key.

Each case runs in runs/<hash>/ (case.json, run.log, result.json, S11.csv). A case that already has a
result.json with metrics is not re-run. runs/index.jsonl gets one line per finished run.
The cache key contains the board PATH, not its content: never overwrite an exported board.json in place,
export a changed board into a new build/<rev>/ folder.
"""
import hashlib
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import antenna as ant  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, 'runs')
PY = sys.executable
MODEL = 'm3'          # bump when sim_board.py or antenna.py change the model or the outputs (m3: port tab to the ground at the notch bottom; m2: battery clip as a solid bar; fractional n made continuous 2026-11-14 without a bump, no m2 run had a fractional n)


def case_hash(case):
	return hashlib.sha1(json.dumps(case, sort_keys=True).encode()).hexdigest()[:10]


def normalise(case):
	c = {'model': MODEL, 'ports': 'feed', 'battery': True, 'mask': 'none', 'er_scale': 1.0, 'nf2ff': True}
	c.update(case)
	a = dict(c['antenna'])
	a.setdefault('family', 'mifa')
	full = ant.params(a)              # every parameter in the key, so a change of antenna.DEFAULTS cannot reuse old runs
	full.update({k: v for k, v in a.items() if k in ant.KEEP_KEYS})
	c['antenna'] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in full.items()}
	if c['ports'] == 'trace' and 'trace_port' not in c:     # port on the routed feed trace (feedport.py), in the key
		import feedport
		pa = c.get('port_at') or {}               # {"ref": "L2", "net": "Net-(U2-ANT)"}: port at another pad (parts runs)
		c['trace_port'] = feedport.trace_port(json.load(open(os.path.join(HERE, c['board']))), c['antenna'],
			length=pa.get('len', 0.4), ref=pa.get('ref'), net=pa.get('net'))
	return c


def load(h):
	p = os.path.join(RUNS, h, 'result.json')
	if os.path.exists(p):
		try:
			r = json.load(open(p))
			return r if ('metrics' in r or 'error' in r) else None
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
	# the same case twice in one list runs once
	seen, uniq = set(), []
	for k in todo:
		if hashes[k] not in seen:
			seen.add(hashes[k])
			uniq.append(k)
	todo = uniq
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
			with open(os.path.join(RUNS, 'index.jsonl'), 'a') as fh:
				fh.write(json.dumps({'hash': hashes[k], 'name': names[k], 'tag': tag, 'purpose': purposes[k], 'time': time.time(),
					'dt': time.time() - t0, 'ok': bool(r and 'metrics' in r),
					'metrics': r.get('metrics') if r else None, 'eff': r.get('eff') if r else None,
					'case': cases[k]}) + '\n')
	results = [load(h) for h in hashes]
	return [dict(r or {}, hash=h) for r, h in zip(results, hashes)]


def line(name, r):
	m = r.get('metrics')
	if not m:
		return '%-30s %s  FAILED %s' % (name, r['hash'], r.get('error'))
	return '%-30s %s  min %6.2f dB @ %.3f GHz  BLE worst %6.2f  Z(2.44) %.1f%+.1fj  eff %s  %s' % (
		name, r['hash'], m['s_min'], m['f_min'] / 1e9, m['ble_worst'], *m['Z_2440'],
		[round(e['rad_eff'], 2) for e in r['eff']] if r.get('eff') else '-',
		'%.1fx%.1f mm' % (r['size']['w'], r['size']['h']) if r.get('size') else '')


if __name__ == '__main__':
	lst = json.load(open(sys.argv[1]))
	par = int(sys.argv[2]) if len(sys.argv) > 2 else 4
	thr = int(sys.argv[3]) if len(sys.argv) > 3 else 5
	tag = os.path.splitext(os.path.basename(sys.argv[1]))[0]
	res = run_cases([x['case'] for x in lst], par, thr, tag, [x.get('name', '') for x in lst],
		[x.get('purpose', '') for x in lst])
	for x, r in zip(lst, res):
		print(line(x.get('name', ''), r))

"""Tune a list of antennas to a target frequency on the server, all candidates in lock step (one runner batch
per iteration), so every topology can be compared at the same frequency.

Usage (server):  python tune.py cases/<list>.json [parallel] [threads]
Each list item: {"name", "purpose", "case", "tune": {...}} with
    param   the continuous length parameter to adjust (default "n": meander fingers; "H", "A", "P" also work)
    f       target frequency (default 2.465e9: 2.44 GHz plus 1 % for the solder mask, which is not in the model,
            the mask moved the BSN IFA down by 1 %)
    metric  "Rmax" (default): frequency of the parallel resonance (maximum of R at the feed), always visible even
            when the antenna is far from 50 ohm. "S11min": frequency of the S11 minimum.
    tol     frequency tolerance (default 10e6)
    iters   maximum EM runs per candidate (default 6)
    match   "S": also move the short-to-feed spacing S so that Rmax approaches 50 ohm (R grows with S), done when
            Rmax is within 35-75 ohm or S hits a geometry rule
    lo, hi  bounds of the parameter
Each step scales the centre-line length (antenna.length) by (f_res / f)^(1/alpha), alpha from the last two runs (1 at first).
Smoke test 2026-11-14 (30 mm disc, CR1632, n 4, H 4, S 1.6): parallel resonance near 3.0 GHz with Rmax about
630 ohm, the S11 minimum sat at the 3.4 GHz band edge, hence the Rmax metric.
A step that breaks a geometry rule (antenna.check on the board) is halved until it passes.
Log: opt/<list>.json (history of every candidate). The runs themselves are ordinary cached runner.py runs.
"""
import copy
import math
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import antenna as ant  # noqa: E402
import runner  # noqa: E402


def solve_length(a, param, target_len, lo, hi):
	"""Parameter value giving the target centre-line length (bisection, length grows with the parameter)."""
	def L(v):
		b = dict(a)
		b[param] = v
		return ant.length(b)
	if L(lo) > target_len:
		return lo
	if L(hi) < target_len:
		return hi
	for _ in range(60):
		m = (lo + hi) / 2
		lo, hi = (m, hi) if L(m) < target_len else (lo, m)
	return (lo + hi) / 2


def legal(a, board, param, old, new):
	for _ in range(8):
		b = dict(a)
		b[param] = round(new, 4)
		if not ant.check(b, board):
			return round(new, 4)
		new = (old + new) / 2
	return old


def main():
	lst = json.load(open(sys.argv[1]))
	par = int(sys.argv[2]) if len(sys.argv) > 2 else min(len(lst), 5)
	thr = int(sys.argv[3]) if len(sys.argv) > 3 else max(20 // par, 1)
	tag = os.path.splitext(os.path.basename(sys.argv[1]))[0]
	os.makedirs(os.path.join(HERE, 'opt'), exist_ok=True)
	logp = os.path.join(HERE, 'opt', tag + '.json')
	state = []
	for it in lst:
		t = dict({'param': 'n', 'f': 2.465e9, 'metric': 'Rmax', 'tol': 10e6, 'iters': 6, 'match': None}, **it.get('tune', {}))
		t.setdefault('lo', {'n': 0.5, 'H': 1.5, 'A': 0.8, 'P': 0.6, 'R': 0.5}.get(t['param'], 0.1))
		t.setdefault('hi', {'n': 14.0, 'H': 12.0, 'A': 20.0, 'P': 4.0, 'R': 14.0}.get(t['param'], 50.0))
		c = copy.deepcopy(it['case'])
		c['antenna'] = ant.params(c['antenna'])
		c['antenna'].update({k: v for k, v in it['case']['antenna'].items() if k in ant.KEEP_KEYS})
		board = json.load(open(os.path.join(HERE, c['board'])))
		state.append({'name': it.get('name', ''), 'purpose': it.get('purpose', ''), 'case': c, 'tune': t, 'board': board,
			'hist': [], 'done': False})
	for k in range(max(s['tune']['iters'] for s in state)):
		act = [s for s in state if not s['done'] and len(s['hist']) < s['tune']['iters']]
		if not act:
			break
		res = runner.run_cases([s['case'] for s in act], min(par, len(act)), thr, tag,
			['%s it%d' % (s['name'], k) for s in act], [s['purpose'] for s in act])
		for s, r in zip(act, res):
			t, a = s['tune'], s['case']['antenna']
			m = r.get('metrics')
			if not m:
				s['hist'].append({'hash': r['hash'], 'error': r.get('error')})
				s['done'] = True
				continue
			p = a[t['param']]
			if t['metric'] == 'Rmax':
				fres, inter = m['f_Rmax'], 1.65e9 < m['f_Rmax'] < 3.35e9
			else:
				fres, inter = m['f_min'], m['min_interior']
			s['hist'].append({'hash': r['hash'], t['param']: p, 'S': a['S'], 'L': ant.length(a), 'f_res': fres, 'f_min': m['f_min'], 's_min': m['s_min'],
				'f_Rmax': m['f_Rmax'], 'Rmax': m['Rmax'], 'Z_fmin': m['Z_fmin'], 'ble_worst': m['ble_worst'], 'interior': inter})
			print('%-28s it%d %s=%.3f S=%.2f  f_res %.3f GHz  Rmax %.0f ohm  S11 min %.1f dB @ %.3f GHz' % (s['name'], k, t['param'],
				p, a['S'], fres / 1e9, m['Rmax'], m['s_min'], m['f_min'] / 1e9), flush=True)
			f_ok = abs(fres - t['f']) < t['tol'] and inter
			m_ok = t['match'] != 'S' or 35 < m['Rmax'] < 75
			if f_ok and m_ok:
				s['done'] = True
				continue
			# length parameter
			if not f_ok:
				# f ~ L^-alpha over the centre-line length L (which includes S, so it also works while S moves),
				# alpha from the last two interior runs, 1 until there are two
				h = [x for x in s['hist'] if 'f_res' in x and x['interior']]
				alpha = 1.0
				if len(h) >= 2 and abs(h[-1]['L'] - h[-2]['L']) > 0.05:
					al = -math.log(h[-1]['f_res'] / h[-2]['f_res']) / math.log(h[-1]['L'] / h[-2]['L'])
					if al > 0:
						alpha = min(max(al, 0.3), 2.5)
				new = solve_length(a, t['param'], ant.length(a) * (fres / t['f']) ** (1 / alpha), t['lo'], t['hi'])
				new = min(max(new, t['lo'], p * 0.5), t['hi'], p * 1.8)
				a[t['param']] = legal(a, s['board'], t['param'], p, new)
			# match: R at the S11 minimum grows with the short-to-feed spacing S
			if t['match'] == 'S' and inter and not m_ok:
				S = a['S']
				a['S'] = legal(a, s['board'], 'S', S, S * min(max((50.0 / m['Rmax']) ** 0.4, 0.6), 1.5))
			if not ant.check(a, s['board']) and s['hist'][-1].get(t['param']) == a[t['param']] and s['hist'][-1]['S'] == a['S']:
				s['done'] = True                 # no legal move left
		json.dump([{k2: v for k2, v in s.items() if k2 != 'board'} for s in state], open(logp, 'w'), indent=1)
	print('\nfinal')
	for s in state:
		h = [x for x in s['hist'] if 'f_res' in x]
		if h:
			b = min(h, key=lambda x: abs(x['f_res'] - s['tune']['f']))
			print('%-28s %s  %s=%.3f S=%.2f  f_res %.3f GHz  Rmax %.0f ohm  S11 min %.1f dB @ %.3f  BLE worst %.1f dB' % (
				s['name'], b['hash'], s['tune']['param'], b[s['tune']['param']], b['S'], b['f_res'] / 1e9, b['Rmax'], b['s_min'],
				b['f_min'] / 1e9, b['ble_worst']))
		else:
			print('%-28s failed %s' % (s['name'], s['hist']))


if __name__ == '__main__':
	main()

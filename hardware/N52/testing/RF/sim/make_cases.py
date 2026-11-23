"""Write a case list (runner.py / tune.py) for a grid of MIFA parameters.

Usage:
    python make_cases.py cases/<name>.json --board build/disc30/board.json --grid n=3,4,5 H=3.5,4.5 \
        [--base '{"W": 0.4}'] [--site '{"x": -4}'] [--case '{"battery": false}'] [--tune n] [--f 2.44e9] \
        [--match S] [--iters 6] --purpose "why these runs are made"

Every combination of the grid becomes one item. Combinations that break a geometry rule on the board
(antenna.check) are left out and listed. With --tune each item gets a "tune" block for tune.py.
"""
import argparse
import itertools
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import antenna as ant  # noqa: E402


def num(s):
	v = float(s)
	return int(v) if v.is_integer() and 'e' not in s and '.' not in s else v


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('out')
	ap.add_argument('--board', required=True)
	ap.add_argument('--grid', nargs='*', default=[])
	ap.add_argument('--base', default='{}')
	ap.add_argument('--site', default='{}')
	ap.add_argument('--case', default='{}')
	ap.add_argument('--tune', default='')
	ap.add_argument('--f', type=float, default=2.465e9)
	ap.add_argument('--match', default=None)
	ap.add_argument('--iters', type=int, default=6)
	ap.add_argument('--purpose', default='')
	ap.add_argument('--prefix', default='')
	a = ap.parse_args()
	board = json.load(open(os.path.join(HERE, a.board)))
	keys, vals = [], []
	for g in a.grid:
		k, v = g.split('=')
		keys.append(k)
		vals.append([num(x) for x in v.split(',')])
	out, bad = [], []
	for combo in itertools.product(*vals) if keys else [()]:
		an = {'family': 'mifa'}
		an.update(json.loads(a.base))
		an.update(dict(zip(keys, combo)))
		s = json.loads(a.site)
		if s:
			an['site'] = s
		name = a.prefix + ' '.join('%s%g' % kv for kv in zip(keys, combo))
		errs = ant.check(an, board)
		if errs:
			bad.append((name, errs))
			continue
		c = {'board': a.board, 'antenna': an}
		c.update(json.loads(a.case))
		item = {'name': name or 'base', 'purpose': a.purpose, 'case': c}
		if a.tune:
			item['tune'] = {'param': a.tune, 'f': a.f, 'iters': a.iters}
			if a.match:
				item['tune']['match'] = a.match
		out.append(item)
	os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
	json.dump(out, open(a.out, 'w'), indent=1)
	print('wrote %s: %d cases' % (a.out, len(out)))
	for n, e in bad:
		print('  left out %s: %s' % (n, '; '.join(e)))


if __name__ == '__main__':
	main()

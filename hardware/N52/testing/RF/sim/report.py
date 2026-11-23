"""Design records and the ranked table from the pulled results (./sim.sh pull runs it).

For each run in results/runs/<hash>/ it writes results/designs/<hash>/ (kept, rebuilt with --force):
    summary.md   purpose, antenna parameters and size, KiCad position, S11 / impedance, ideal matching estimate,
                 efficiency, run details
    s11.png      S11 and Zin without parts and with the best ideal 1- and 2-part match at the feed
    geometry.png the board and antenna as simulated
and results/DESIGNS.md: every design ranked by the worst BLE S11 after the best ideal 2-part match, with size.

Efficiency is the raw value of the own far-field transform (farfield.py). The dipole bench reads 102 %, the BSN
board model read 100 % without and 109 % with the battery on a lossless board, so treat it as about +-10 %.

Usage: python report.py [--force]
"""
import glob
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import antenna as ant  # noqa: E402
import match_ideal as mi  # noqa: E402
from draw_antennas import draw_panel  # noqa: E402

RES = os.path.join(HERE, 'results')
OUT = os.path.join(RES, 'designs')
BLE = (2.400e9, 2.4835e9)


def load_board(path, cache={}):
	if path not in cache:
		p = os.path.join(HERE, path)
		cache[path] = json.load(open(p)) if os.path.exists(p) else None
	return cache[path]


def s11_plot(path, f, Z, r, title):
	fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
	for net, lab, st in (([], 'no parts', '-'), (r['one'][1], 'ideal 1 part: ' + mi.describe(r['one'][1]), '--'),
			(r['two'][1], 'ideal 2 parts: ' + mi.describe(r['two'][1]), ':')):
		z = mi.apply(Z, f, net)
		a1.plot(f / 1e9, 20 * np.log10(np.abs((z - 50) / (z + 50))), st, label=lab)
	a1.axvspan(BLE[0] / 1e9, BLE[1] / 1e9, color='g', alpha=0.12)
	a1.axhline(-10, color='k', lw=0.6)
	a1.set_xlabel('f (GHz)')
	a1.set_ylabel('S11 (dB)')
	a1.set_ylim(-30, 0)
	a1.legend(fontsize=7)
	a1.grid(alpha=0.3)
	a2.plot(f / 1e9, Z.real, label='R')
	a2.plot(f / 1e9, Z.imag, label='X')
	a2.axvspan(BLE[0] / 1e9, BLE[1] / 1e9, color='g', alpha=0.12)
	a2.axhline(50, color='k', lw=0.6, ls='--')
	a2.set_xlabel('f (GHz)')
	a2.set_ylabel('Zin at the feed (ohm)')
	a2.set_ylim(-300, 300)
	a2.legend(fontsize=7)
	a2.grid(alpha=0.3)
	fig.suptitle(title, fontsize=9)
	fig.tight_layout()
	fig.savefig(path, dpi=100)
	plt.close(fig)


def record(h, force):
	d = os.path.join(RES, 'runs', h)
	r = json.load(open(os.path.join(d, 'result.json')))
	if 'metrics' not in r:
		return None
	c = json.load(open(os.path.join(d, 'case.json'))) if os.path.exists(os.path.join(d, 'case.json')) else r['case']
	o = os.path.join(OUT, h)
	m = r['metrics']
	mt = mi.analyse(d)
	a = dict(r.get('params') or ant.params(c['antenna']))     # the parameters the run used, not today's defaults
	a.update({k: v for k, v in c['antenna'].items() if k in ant.KEEP_KEYS})
	c = dict(c, antenna=a)
	eff = r.get('eff') or []
	e244 = [e for e in eff if abs(e['f'] - 2.44e9) < 1e6]
	row = {'hash': h, 'name': c.get('name', ''), 'tag': c.get('tag', ''), 'board': c['board'], 'model': c.get('model'),
		'battery': c.get('battery'), 'desc': ant.describe(a), 'size': ant.size(a), 'f_min': m['f_min'], 's_min': m['s_min'],
		'ble_none': mt['none'], 'ble_1': mt['one'][0], 'ble_2': mt['two'][0], 'match1': mi.describe(mt['one'][1]),
		'match2': mi.describe(mt['two'][1]), 'Z2440': m['Z_2440'], 'rad_eff': e244[0]['rad_eff'] if e244 else None,
		'Dmax': e244[0]['Dmax_dBi'] if e244 else None, 'purpose': c.get('purpose', '')}
	if os.path.exists(os.path.join(o, 'summary.md')) and not force:
		return row
	os.makedirs(o, exist_ok=True)
	s11_plot(os.path.join(o, 's11.png'), mt['f'], mt['Z'], mt, '%s  %s\n%s' % (h, row['name'], row['desc']))
	board = load_board(c['board'])
	geo = None
	if board:
		fig, axs = plt.subplots(1, 2, figsize=(11, 5))
		geo = draw_panel(axs[0], c, board, row['name'])
		draw_panel(axs[1], c, board, 'zoom', zoom=True)
		fig.tight_layout()
		fig.savefig(os.path.join(o, 'geometry.png'), dpi=100)
		plt.close(fig)
	q = a
	L = ['# %s  %s' % (h, row['name']), '', '**Purpose:** %s' % (row['purpose'] or '-'), '',
		'## Antenna', '', '`%s`' % row['desc'], '',
		'| parameter | value |', '|---|---|'] + ['| %s | %g |' % kv for kv in ant.params(q).items()] + [
		'| site | %s |' % json.dumps(ant.site(a, board) if board else a.get('site')), '',
		'Copper %.2f x %.2f mm above the ground edge (%.1f mm2), centre-line length %.1f mm.' % (
			row['size']['w'], row['size']['h'], row['size']['area'], ant.length(a))]
	if geo:
		L += ['KiCad position of the copper: x %.2f..%.2f, y %.2f..%.2f, edge clearance %.2f mm.' % (
			*geo['x'], *geo['y'], geo['edge_clearance'])]
	L += ['', '![geometry](geometry.png)', '', '## Impedance at the feed (port across the notch)', '',
		'| | |', '|---|---|',
		'| S11 minimum | %.1f dB at %.3f GHz |' % (m['s_min'], m['f_min'] / 1e9),
		'| Z at 2.44 GHz | %.1f %+.1fj ohm |' % tuple(m['Z_2440']),
		'| -10 dB band | %s |' % ('%.3f-%.3f GHz' % (m['bw10'][0] / 1e9, m['bw10'][1] / 1e9) if m['bw10'] else '-'),
		'| worst BLE S11, no parts | %.1f dB |' % mt['none'],
		'| worst BLE S11, best ideal 1 part | %.1f dB (%s) |' % (mt['one'][0], row['match1']),
		'| worst BLE S11, best ideal 2 parts | %.1f dB (%s) |' % (mt['two'][0], row['match2']), '',
		'Ideal lossless parts right at the feed, listed from the antenna toward the chip (shunt first = shunt on the antenna side). Real parts on pads with a trace and Q 30-50 give less (BSN: -15.3 dB ideal became -10.9 dB).', '',
		'![S11](s11.png)', '']
	if eff:
		L += ['## Efficiency (raw own far-field transform, about +-10 %)', '', '| f (GHz) | radiation eff. | total eff. (no match) | Dmax (dBi) |', '|---|---|---|---|']
		L += ['| %.2f | %.0f %% | %.0f %% | %.1f |' % (e['f'] / 1e9, 100 * e['rad_eff'], 100 * e['tot_eff'], e['Dmax_dBi']) for e in eff]
		L += ['']
	L += ['## Run', '', 'board `%s`, battery %s, mask %s, model %s, %s cells, %.0f s.' % (
		c['board'], c.get('battery'), c.get('mask'), c.get('model'), r['mesh'].get('ncells'), r.get('t_total', 0)), '']
	open(os.path.join(o, 'summary.md'), 'w', encoding='utf-8').write('\n'.join(L))
	json.dump(row, open(os.path.join(o, 'summary.json'), 'w'), indent=1)
	return row


def main():
	force = '--force' in sys.argv
	rows = []
	for p in sorted(glob.glob(os.path.join(RES, 'runs', '*', 'result.json'))):
		h = os.path.basename(os.path.dirname(p))
		try:
			row = record(h, force)
		except Exception as ex:
			print('record %s failed: %r' % (h, ex))
			continue
		if row:
			rows.append(row)
	rows.sort(key=lambda x: x['ble_2'])
	L = ['# BSN-N52 MIFA designs', '', 'Ranked by the worst S11 over BLE (2.400-2.4835 GHz) after the best ideal 2-part match at the feed. '
		'Size = copper above the ground edge. Efficiency = raw radiation efficiency at 2.44 GHz (about +-10 %).', '',
		'| run | name | board | antenna | size (mm) | S11 min | BLE no parts | 1 part | 2 parts | Z(2.44) | rad. eff |',
		'|---|---|---|---|---|---|---|---|---|---|---|']
	for x in rows:
		L.append('| [%s](designs/%s/summary.md) | %s | %s | %s | %.1f x %.1f | %.1f dB @ %.3f | %.1f | %.1f | %.1f (%s) | %.0f%+.0fj | %s |' % (
			x['hash'], x['hash'], x['name'], os.path.basename(os.path.dirname(x['board'])), x['desc'].split('  (')[0],
			x['size']['w'], x['size']['h'], x['s_min'], x['f_min'] / 1e9, x['ble_none'], x['ble_1'], x['ble_2'], x['match2'],
			x['Z2440'][0], x['Z2440'][1], '%.0f %%' % (100 * x['rad_eff']) if x['rad_eff'] else '-'))
	open(os.path.join(RES, 'DESIGNS.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
	print('wrote results/DESIGNS.md, %d designs' % len(rows))


if __name__ == '__main__':
	main()

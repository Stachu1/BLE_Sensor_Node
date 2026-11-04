"""Archive every finished simulation as a small, self-contained design record (no raw field data).

For each run in results/runs/<hash>/ (pulled with ./sim.sh pull) it writes results/designs/<hash>/:
    summary.md     purpose, antenna dimensions (sim and KiCad coordinates), impedance, ideal matching parts,
                   efficiency and directivity, run details
    summary.json   the same numbers, machine readable
    geometry.png   the board and antenna as simulated
    s11.png        S11 and Zin at J2 without parts and with the best ideal 1- and 2-part match
    pattern.png    directivity cuts and map at 2.44 GHz (runs with pattern.npz only)
and results/DESIGNS.md, a ranked table of all designs with links.

Efficiency is only valid for MODEL v5 and later (own far-field transform, see farfield.py). Earlier runs used
the openEMS NF2FF, which is wrong for our boards, so their efficiency is marked invalid.

Usage: python archive.py [--force]       (existing records are kept unless --force)
"""
import glob
import json
import os
import sys
import time

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
# Efficiency calibration (2026-11-03, lossless FR4 runs of b2 H4.4 L9.7, true value 100 %): the own transform
# reads 100.2 % without the battery and 108.9 % with the CR2032 model. Calibrated = raw / factor.
EFF_CAL = {True: 1.089, False: 1.002}

# why the runs without a "purpose" field were made (by tag)
TAG_PURPOSE = {
	'ref': 'Reference: AE1 as first placed on the rev B board (b1), with explicit solder mask and with lossless FR4 to measure the mask shift and the FR4 loss.',
	'tune_ifa_h30': 'Tuner start points: straight IFA with the arm 3 mm above the ground edge (b1), tuning L and S towards 50 ohm at J2.',
	'tune_ifa_h25': 'Tuner start points: straight IFA with the arm 2.5 mm above the ground edge (b1).',
	'tune_bent_h40': 'Tuner start points: bent-end IFA with the arm 4 mm above the ground edge (b1).',
	'b2_quick': 'First look at the b2 layout (antenna-side shunt pads removed, ground edge 1.4 mm lower): does the lower ground edge help?',
	'diag1': 'Diagnostics of the sim model: battery removed, stricter end criterion, lossless FR4.',
	'b2_cand1': 'Candidates on b2 around the best quick result (arm top at KiCad y 85): length, short-leg spacing, arm width, arm height.',
	'smoke': 'Smoke test of the pipeline.',
	'smoke_tune': 'Smoke test of the tuner.',
}


def kc_rect(r):
	x0, y0, x1, y1 = r
	return [round(x0 + 150, 3), round(100 - y1, 3), round(x1 + 150, 3), round(100 - y0, 3)]


def load_board(path):
	p = os.path.join(HERE, path)
	return json.load(open(p)) if os.path.exists(p) else None


def eff_rows(r):
	model = r['case'].get('model', 'v4')
	valid = model >= 'v5'
	rows = []
	k = EFF_CAL[bool(r['case'].get('battery', True))]
	for e in r.get('eff') or []:
		rows.append({'f': e['f'], 'rad_eff_raw': e['rad_eff'], 'rad_eff': e['rad_eff'] / k, 'tot_eff': e['tot_eff'] / k,
			'Dmax_dBi': e['Dmax_dBi'], 'valid': valid, 'flux_eff': e.get('flux_eff'), 'cal_factor': k})
	return rows, valid


def plot_s11(d, f, Z, nets, title):
	fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
	for net, lab, st in nets:
		z = mi.apply(Z, f, net)
		s = 20 * np.log10(np.abs((z - 50) / (z + 50)))
		ax[0].plot(f / 1e9, s, st, label=lab)
	ax[1].plot(f / 1e9, Z.real, label='R (no parts)')
	ax[1].plot(f / 1e9, Z.imag, '--', label='X (no parts)')
	for a in ax:
		a.axvspan(BLE[0] / 1e9, BLE[1] / 1e9, color='g', alpha=0.1)
		a.grid(alpha=0.3)
		a.set_xlabel('GHz')
		a.legend(fontsize=7)
	ax[0].axhline(-10, color='k', lw=0.5)
	ax[0].set_ylim(-35, 0)
	ax[0].set_ylabel('S11 at J2 (dB)')
	ax[1].set_ylim(-150, 250)
	ax[1].set_ylabel('Zin at J2 (ohm)')
	fig.suptitle(title, fontsize=9)
	fig.tight_layout()
	fig.savefig(os.path.join(d, 's11.png'), dpi=100)
	plt.close(fig)


def plot_pattern(d, pz, title):
	p = np.load(pz)
	th, ph, D = p['theta'], p['phi'], p['D_dBi']
	k = int(np.argmin(np.abs(p['f'] - 2.44e9)))
	Dk = D[k]
	fig = plt.figure(figsize=(13, 4.2))
	cuts = [('XZ cut (phi 0/180)', 0), ('YZ cut (phi 90/270)', 90)]
	for i, (lab, p0) in enumerate(cuts):
		ax = fig.add_subplot(1, 3, i + 1, projection='polar')
		j0 = int(np.argmin(np.abs(ph - p0)))
		j1 = int(np.argmin(np.abs(ph - (p0 + 180))))
		ang = np.concatenate([np.deg2rad(th), 2 * np.pi - np.deg2rad(th[::-1])])
		val = np.concatenate([Dk[:, j0], Dk[::-1, j1]])
		ax.plot(ang, np.maximum(val, -20))
		ax.set_rlim(-20, max(5, np.ceil(val.max())))
		ax.set_theta_zero_location('N')
		ax.set_title(lab + ', dBi', fontsize=8)
	ax = fig.add_subplot(1, 3, 3)
	im = ax.pcolormesh(ph, th, Dk, shading='auto', vmin=-20, vmax=max(5, Dk.max()))
	ax.set_xlabel('phi (deg)')
	ax.set_ylabel('theta (deg)')
	ax.invert_yaxis()
	fig.colorbar(im, ax=ax, label='directivity dBi')
	fig.suptitle(title + '  (z = board normal, F.Cu side theta 0, y = towards the antenna edge, x = along the arm)', fontsize=8)
	fig.tight_layout()
	fig.savefig(os.path.join(d, 'pattern.png'), dpi=100)
	plt.close(fig)


def record(h, r, force=False):
	d = os.path.join(OUT, h)
	sj = os.path.join(d, 'summary.json')
	if os.path.exists(sj) and not force:
		return json.load(open(sj))
	rd = os.path.join(RES, 'runs', h)
	if not os.path.exists(os.path.join(rd, 'S11.csv')):
		return None
	os.makedirs(d, exist_ok=True)
	c = r['case']
	name = c.get('name') or h
	purpose = c.get('purpose') or TAG_PURPOSE.get(c.get('tag', ''), '')
	a = c['antenna']
	board_path = c.get('board', 'build/board.json')
	board = load_board(board_path) if board_path != 'r011' else None
	geo = {}
	if isinstance(a, dict):
		rects, q = ant.rects(a)
		geo = {'family': a['family'], 'base': a.get('base', 'b1'), 'params': {k: q[k] for k in ant.DEFAULTS[a['family']]},
			'rects_sim': [list(x) for x in rects], 'rects_kicad_x0y0x1y1': [kc_rect(x) for x in rects]}
	else:
		geo = {'family': 'placed (AE1 copper from the board file)'}
	if board is not None:
		fig, ax = plt.subplots(figsize=(8, 5))
		ext = draw_panel(ax, c, board, name)
		fig.tight_layout()
		fig.savefig(os.path.join(d, 'geometry.png'), dpi=100)
		plt.close(fig)
		geo.update(ext)
	m = mi.analyse(rd)
	f, Z = m['f'], m['Z']
	plot_s11(d, f, Z, [([], 'no parts (L2 0R)', '-'), (m['one'][1], '1 part: ' + mi.describe(m['one'][1]), '--'),
		(m['two'][1], '2 parts: ' + mi.describe(m['two'][1]), ':')], name)
	zs = {}
	for fz in (2.40e9, 2.44e9, 2.48e9):
		k = int(np.argmin(np.abs(f - fz)))
		zs['%.2f' % (fz / 1e9)] = [round(float(Z[k].real), 2), round(float(Z[k].imag), 2)]
	effs, valid = eff_rows(r)
	pz = os.path.join(rd, 'pattern.npz')
	if valid and os.path.exists(pz):
		plot_pattern(d, pz, name)
	met = r['metrics']
	s = {'hash': h, 'name': name, 'purpose': purpose, 'tag': c.get('tag', ''), 'model': c.get('model', 'v4'),
		'board': board_path, 'battery': c.get('battery', True), 'mask': c.get('mask', 'none'), 'er_scale': c.get('er_scale', 1.0),
		'tand_scale': c.get('tand_scale', 1.0), 'mesh': c.get('mesh', {}), 'ports': c.get('ports', 'j2'), 'geometry': geo,
		'f_s11_min_GHz': round(met['f_min'] / 1e9, 4), 's11_min_dB': round(met['s_min'], 2), 'ble_worst_no_parts_dB': round(m['none'], 2),
		'bw10_MHz': met['bw10'] and [round(met['bw10'][0] / 1e6), round(met['bw10'][1] / 1e6)],
		'Z_J2_ohm': zs, 'match_1part': {'parts': mi.describe(m['one'][1]), 'net': m['one'][1], 'ble_worst_dB': round(m['one'][0], 2)},
		'match_2part': {'parts': mi.describe(m['two'][1]), 'net': m['two'][1], 'ble_worst_dB': round(m['two'][0], 2)},
		'efficiency': effs, 'efficiency_valid': valid, 'cells': r.get('mesh', {}).get('ncells'),
		'run_s': round(r.get('t_total', 0))}
	json.dump(s, open(sj, 'w'), indent=1)
	L = ['# %s' % name, '', '**Why this run:** %s' % (purpose or 'not recorded'), '',
		'Run `%s`, tag `%s`, model %s, board `%s`, battery %s, mask %s%s.' % (h, s['tag'], s['model'], board_path,
			'yes' if s['battery'] else 'no', s['mask'], '' if s['er_scale'] == 1 else ', er x%.2f' % s['er_scale']), '',
		'![geometry](geometry.png)', '', '## Antenna']
	if 'params' in geo:
		L += ['', '%s, ground edge base %s: %s' % (geo['family'], geo['base'], ', '.join('%s %g mm' % kv for kv in geo['params'].items())), '',
			'| part | KiCad x0 | y0 | x1 | y1 |', '|---|---|---|---|---|']
		labels = ['short leg', 'feed leg', 'arm', 'drop', 'return']
		for lab, rr in zip(labels, geo['rects_kicad_x0y0x1y1']):
			L.append('| %s | %.2f | %.2f | %.2f | %.2f |' % (lab, *rr))
	else:
		L += ['', geo['family']]
	if 'edge_clearance' in geo:
		L += ['', 'Copper extent x %.2f..%.2f, y %.2f..%.2f (KiCad), smallest distance to the board edge %.2f mm.' % (
			*geo['x'], *geo['y'], geo['edge_clearance'])]
	L += ['', '## Impedance and match at J2', '',
		'Best match without parts %.1f dB at %.3f GHz, worst BLE channel %.1f dB, -10 dB band %s MHz.' % (
			s['s11_min_dB'], s['f_s11_min_GHz'], s['ble_worst_no_parts_dB'], s['bw10_MHz'] or 'none'), '',
		'Z at J2: ' + ', '.join('%s GHz %.1f%+.1fj ohm' % (k, *v) for k, v in zs.items()), '',
		'| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |', '|---|---|',
		'| none (L2 0R) | %.1f dB |' % s['ble_worst_no_parts_dB'],
		'| 1 part: %s | %.1f dB |' % (s['match_1part']['parts'], s['match_1part']['ble_worst_dB']),
		'| 2 parts: %s | %.1f dB |' % (s['match_2part']['parts'], s['match_2part']['ble_worst_dB']), '',
		'![s11](s11.png)', '', '## Efficiency and pattern', '']
	if effs and valid:
		L += ['| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |', '|---|---|---|---|']
		L += ['| %.2f | %.0f %% | %.0f %% | %.1f |' % (e['f'] / 1e9, 100 * e['rad_eff'], 100 * e['tot_eff'], e['Dmax_dBi']) for e in effs]
		L += ['', 'Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.']
		if os.path.exists(os.path.join(d, 'pattern.png')):
			L += ['', '![pattern](pattern.png)']
	elif effs:
		L += ['Not valid: this run used the openEMS NF2FF transform (model %s), which is wrong for this board.' % s['model']]
	else:
		L += ['Not computed.']
	L += ['', 'Mesh %s cells, run time %d min.' % (s['cells'], s['run_s'] / 60)]
	open(os.path.join(d, 'summary.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
	return s


def main():
	force = '--force' in sys.argv
	runs = {}
	for p in glob.glob(os.path.join(RES, 'runs', '*', 'result.json')):
		h = os.path.basename(os.path.dirname(p))
		try:
			r = json.load(open(p))
		except Exception:
			continue
		a = r.get('case', {}).get('antenna')
		if isinstance(a, dict) and ant.check(a):
			print('skip %s (geometry now invalid: %s)' % (h, ant.check(a)))
			continue
		if 'metrics' in r and r['case'].get('board') != 'r011' and 'smoke' not in r['case'].get('tag', '') + r['case'].get('name', ''):
			runs[h] = r
	recs = []
	for h, r in runs.items():
		try:
			s = record(h, r, force)
		except Exception as ex:
			print('skip', h, repr(ex))
			continue
		if s:
			recs.append(s)
	recs.sort(key=lambda s: (s['ports'] != 'j2', s['match_2part']['ble_worst_dB']))
	L = ['# C23 antenna designs (generated by archive.py, %s)' % time.strftime('%Y-%m-%d %H:%M'), '',
		'Every simulated design, best first by the worst BLE-channel S11 at J2 after the best ideal 2-part match '
		'(L2 series, L3 shunt). Efficiency only from model v5 runs (own far-field transform). '
		'Each link has the dimensions, drawing, S11, pattern and the reason for the run.', '',
		'| design | board | f(S11 min) GHz | worst BLE dB: none / 1 part / 2 parts | parts (2) | rad. eff. 2.44 | Dmax dBi | |',
		'|---|---|---|---|---|---|---|---|']
	for s in recs:
		e = [x for x in s['efficiency'] if abs(x['f'] - 2.44e9) < 1e6]
		ef = '%.0f %%' % (100 * e[0]['rad_eff']) if e and s['efficiency_valid'] else '-'
		dm = '%.1f' % e[0]['Dmax_dBi'] if e and s['efficiency_valid'] else '-'
		L.append('| %s | %s | %.3f | %.1f / %.1f / %.1f | %s | %s | %s | [record](designs/%s/summary.md) |' % (
			s['name'], ('b1' if s['board'] == 'build/board.json' else os.path.basename(os.path.dirname(s['board']))), s['f_s11_min_GHz'], s['ble_worst_no_parts_dB'],
			s['match_1part']['ble_worst_dB'], s['match_2part']['ble_worst_dB'], s['match_2part']['parts'], ef, dm, s['hash']))
	open(os.path.join(RES, 'DESIGNS.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
	print('wrote', len(recs), 'records and results/DESIGNS.md')


if __name__ == '__main__':
	main()

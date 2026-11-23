"""Figures for the final BSN-N52 r7 antenna check (matched network, solder mask, cell fitted).

Inputs (copied from the server, see README):
    data/<set>/matched.npz, matched.json, pattern.npz     combine_multi.py output of a 4-port run set
    ../results/runs/<hash>/S11.csv                         1-port reference runs (port at the L1 pad, no parts)
Writes figures/*.png and data/summary.json.

Usage:  python make_figures.py [final set] [smoke set]
"""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from combine_multi import z_ind, z_cap, Z0  # noqa: E402

FINAL = sys.argv[1] if len(sys.argv) > 1 else 'final'
SMOKE = sys.argv[2] if len(sys.argv) > 2 else 'smoke4'
REF_NOMASK, REF_MASK = 'cdb92f514c', '1d7585b9c4'      # 1-port at L1, normal mesh, without / with the 20 um mask
FIG = os.path.join(HERE, 'figures')
os.makedirs(FIG, exist_ok=True)
BLE = (2.402e9, 2.480e9)
C = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']
INK, INK2, GRID = '#1f1f1e', '#5f5e59', '#e4e3df'
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2,
	'ytick.color': INK2, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.8, 'axes.spines.top': False,
	'axes.spines.right': False, 'lines.linewidth': 2, 'legend.frameon': False, 'figure.dpi': 130})
PARTS = {'L2': 3.3e-9, 'C1': 1.0e-12, 'L1': 5.1e-9}
TOL = {'L2': 0.1e-9, 'C1': 0.05e-12, 'L1': 0.1e-9}     # LQW15AN ...B (+-0.1 nH), GJM15 ...B (+-0.05 pF)
QL, QC, CP, ESL = 50.0, 100.0, 0.08e-12, 0.3e-9


def load_set(name):
	d = os.path.join(HERE, 'data', name)
	if not os.path.exists(os.path.join(d, 'matched.npz')):
		return None
	m = dict(np.load(os.path.join(d, 'matched.npz')))
	m['json'] = json.load(open(os.path.join(d, 'matched.json')))
	p = os.path.join(d, 'pattern.npz')
	m['pattern'] = dict(np.load(p)) if os.path.exists(p) else None
	return m


def load_ref(h):
	p = os.path.join(HERE, '..', 'results', 'runs', h, 'S11.csv')
	if not os.path.exists(p):
		return None
	a = np.loadtxt(p, delimiter=',', skiprows=1)
	return a[:, 0], a[:, 4] + 1j * a[:, 5]


def gin_of(S, f, parts, fscale=1.0):
	"""Matched input reflection of the 4-port S (f, 4, 4) with the parts, response shifted by fscale."""
	if fscale != 1.0:                              # the board at er (1 +- d): the whole response moves in frequency
		fs = f * fscale
		S = np.stack([np.stack([np.interp(f, fs, S[:, i, j].real) + 1j * np.interp(f, fs, S[:, i, j].imag)
			for j in range(4)], 1) for i in range(4)], 1)
	w = 2 * np.pi * f
	ZL = np.stack([z_ind(parts['L2'], w, QL, CP), z_cap(parts['C1'], w, QC, ESL), z_ind(parts['L1'], w, QL, CP)], 1)
	G = (ZL - Z0) / (ZL + Z0)
	out = np.zeros(len(f), complex)
	for j in range(len(f)):
		s = S[j]
		br = np.linalg.solve(np.eye(3) - s[1:, 1:] @ np.diag(G[j]), s[1:, 0])
		out[j] = s[0, 0] + s[0, 1:] @ (G[j] * br)
	return out


def cascade_1port(f, Za, parts):
	"""Ideal-wiring cascade (match_tee.py): radio - L2 series - C1 shunt - L1 series - antenna Za, no pads or traces."""
	w = 2 * np.pi * f
	z = Za + z_ind(parts['L1'], w, QL, CP)
	yc = 1 / z_cap(parts['C1'], w, QC, ESL)
	z = 1 / (1 / z + yc) + z_ind(parts['L2'], w, QL, CP)
	return (z - Z0) / (z + Z0)


def db(x):
	return 20 * np.log10(np.abs(x))


def shade_ble(ax):
	ax.axvspan(BLE[0] / 1e9, BLE[1] / 1e9, color='#f1efe8', zorder=0, lw=0)
	ax.text((BLE[0] + BLE[1]) / 2e9, 0.98, 'BLE', transform=ax.get_xaxis_transform(), ha='center', va='top', color=INK2, fontsize=9)


def fig_s11(fin, smoke, refs, summ):
	fig, ax = plt.subplots(figsize=(8, 4.6))
	shade_ble(ax)
	lines = []
	if fin is not None:
		lines.append((fin['f'], db(fin['gin']), C[0], 'full model, high-res mesh + mask, real parts (final)'))
	if smoke is not None:
		lines.append((smoke['f'], db(smoke['gin']), C[1], 'full model, normal mesh, no mask'))
	if refs.get('mask'):
		f, Za = refs['mask']
		lines.append((f, db(cascade_1port(f, Za, PARTS)), C[2], 'antenna run + ideal wiring of the parts (match_tee), mask'))
	for f, y, c, lab in lines:
		ax.plot(f / 1e9, y, color=c, label=lab)
	ax.axhline(-10, color=INK2, lw=0.8, ls='--')
	ax.set_xlim(2.2, 2.7)
	ax.set_ylim(-30, 0)
	ax.set_xlabel('frequency (GHz)')
	ax.set_ylabel('S11 at the radio pin (dB)')
	ax.set_title('Input match with L2 3.3 nH, C1 1.0 pF, L1 5.1 nH (CR1632 fitted)', loc='left', color=INK)
	ax.legend(loc='lower left', fontsize=8.5)
	fig.tight_layout()
	fig.savefig(os.path.join(FIG, 's11_matched.png'))
	plt.close(fig)


def smith_grid(ax):
	t = np.linspace(0, 2 * np.pi, 361)
	ax.plot(np.cos(t), np.sin(t), color=INK2, lw=1)
	for r in (0.2, 0.5, 1, 2, 5):
		z = r + 1j * np.concatenate([[0], np.geomspace(1e-3, 50, 400)])
		for s in (1, -1):
			g = (z.real + 1j * s * z.imag - 1) / (z.real + 1j * s * z.imag + 1)
			ax.plot(g.real, g.imag, color=GRID, lw=0.8)
	for x in (0.2, 0.5, 1, 2, 5):
		for s in (1, -1):
			z = np.concatenate([[0], np.geomspace(1e-3, 50, 400)]) + 1j * s * x
			g = (z - 1) / (z + 1)
			ax.plot(g.real, g.imag, color=GRID, lw=0.8)
	ax.plot([-1, 1], [0, 0], color=GRID, lw=0.8)
	t = np.linspace(0, 2 * np.pi, 181)
	ax.plot(np.sqrt(0.1) * np.cos(t), np.sqrt(0.1) * np.sin(t), color=INK2, lw=0.8, ls='--')
	ax.text(0, -np.sqrt(0.1) - 0.04, '-10 dB', ha='center', va='top', fontsize=8, color=INK2, clip_on=True)
	ax.set_aspect('equal')
	ax.axis('off')


def fig_smith(fin, refs):
	fig, ax = plt.subplots(figsize=(5.4, 5.4))
	smith_grid(ax)
	sets = []
	if fin is not None:
		sets.append((fin['f'], fin['gin'], C[0], 'radio pin, matched (final)'))
	if refs.get('mask'):
		f, Za = refs['mask']
		sets.append((f, (Za - Z0) / (Za + Z0), C[1], 'antenna at the L1 pad, no parts'))
	for f, g, c, lab in sets:
		sel = (f >= 2.2e9) & (f <= 2.7e9)
		ax.plot(g[sel].real, g[sel].imag, color=c, label=lab)
		for fm in (2.40e9, 2.44e9, 2.48e9):
			j = int(np.argmin(np.abs(f - fm)))
			ax.plot(g[j].real, g[j].imag, 'o', ms=6, color=c, mec='white', mew=1.5)
			ax.annotate('%.2f' % (fm / 1e9), (g[j].real, g[j].imag), xytext=(5, 4), textcoords='offset points', fontsize=8, color=INK)
	ax.legend(loc='upper left', bbox_to_anchor=(-0.02, 1.08), fontsize=8.5)
	ax.set_title('2.2-2.7 GHz, markers 2.40 / 2.44 / 2.48 GHz', fontsize=9, color=INK2, y=-0.06)
	fig.tight_layout()
	fig.savefig(os.path.join(FIG, 'smith.png'))
	plt.close(fig)


def fig_budget(fin, summ):
	e = fin['json']['eff']
	cats = [('radiated', lambda x: x['tot_eff'], C[0]),
		('board, cell and FR4 loss', lambda x: x['into_antenna'] - x['tot_eff'], C[3]),
		('L2 loss', lambda x: x['loss_L2'], C[1]),
		('C1 loss', lambda x: x['loss_C1'], C[4]),
		('L1 loss', lambda x: x['loss_L1'], C[6]),
		('reflected (mismatch)', lambda x: x['mismatch_frac'], C[7])]
	fig, ax = plt.subplots(figsize=(8, 3.2))
	ylab = ['%.2f GHz' % (x['f'] / 1e9) for x in e]
	left = np.zeros(len(e))
	for name, fn, c in cats:
		v = np.array([100 * fn(x) for x in e])
		ax.barh(ylab, v, left=left, color=c, label=name, edgecolor='white', linewidth=2, height=0.55)
		for k, (l, vv) in enumerate(zip(left, v)):
			if vv > 6:
				ax.text(l + vv / 2, k, '%.0f %%' % vv, ha='center', va='center', color='white', fontsize=8.5)
		left += v
	ax.set_xlim(0, 100)
	ax.invert_yaxis()
	ax.set_xlabel('share of the power the radio delivers to a 50 ohm load (%)')
	ax.grid(axis='y', visible=False)
	ax.legend(ncol=3, loc='lower left', bbox_to_anchor=(0, 1.02), fontsize=8.5)
	fig.tight_layout()
	fig.savefig(os.path.join(FIG, 'power_budget.png'))
	plt.close(fig)


def fig_tolerance(fin, summ, n=400):
	rng = np.random.default_rng(1)
	f, S = fin['f'], fin['S']
	sel = (f > 2.25e9) & (f < 2.65e9)
	f, S = f[sel], S[sel]
	nom = db(gin_of(S, f, PARTS))
	curves, worst = [], []
	ble = (f >= BLE[0]) & (f <= BLE[1])
	for _ in range(n):
		p = {k: v + rng.uniform(-1, 1) * TOL[k] for k, v in PARTS.items()}
		s = rng.uniform(0.99, 1.01)
		y = db(gin_of(S, f, p, s))
		curves.append(y)
		worst.append(y[ble].max())
	curves = np.array(curves)
	fig, ax = plt.subplots(figsize=(8, 4.2))
	shade_ble(ax)
	ax.fill_between(f / 1e9, curves.min(0), curves.max(0), color='#b7d3f6', lw=0, label='spread: parts within tolerance, board er +-2 % (+-1 % in f)')
	ax.plot(f / 1e9, nom, color=C[0], label='nominal (final run)')
	ax.axhline(-10, color=INK2, lw=0.8, ls='--')
	ax.set_xlim(2.25, 2.65)
	ax.set_ylim(-30, 0)
	ax.set_xlabel('frequency (GHz)')
	ax.set_ylabel('S11 at the radio pin (dB)')
	ax.set_title('Tolerance spread of the matched input (%d random boards)' % n, loc='left', color=INK)
	ax.legend(loc='lower left', fontsize=8.5)
	fig.tight_layout()
	fig.savefig(os.path.join(FIG, 'tolerance.png'))
	plt.close(fig)
	worst = np.array(worst)
	summ['tolerance'] = {'n': n, 'worst_ble_dB_nominal': float(nom[ble].max()),
		'worst_ble_dB_p50': float(np.percentile(worst, 50)), 'worst_ble_dB_p95': float(np.percentile(worst, 95)),
		'worst_ble_dB_max': float(worst.max()), 'tol': {k: v for k, v in TOL.items()}, 'f_scale': 0.01}


def fig_pattern(fin):
	p = fin['pattern']
	k = int(np.argmin(np.abs(p['f'] - 2.44e9)))
	D, th, ph = p['D_dBi'][k], p['theta'], p['phi']
	fig, axs = plt.subplots(1, 3, figsize=(11, 4), subplot_kw={'projection': 'polar'})
	cuts = [('xz plane (phi 0)', np.r_[D[:, list(ph).index(0)], D[::-1, list(ph).index(180)][1:]], np.r_[th, 360 - th[::-1][1:]]),
		('yz plane (phi 90)', np.r_[D[:, list(ph).index(90)], D[::-1, list(ph).index(270)][1:]], np.r_[th, 360 - th[::-1][1:]]),
		('xy plane (theta 90)', D[list(th).index(90), :], ph)]
	for ax, (title, d, ang) in zip(axs, cuts):
		ax.plot(np.deg2rad(ang), np.maximum(d, -20), color=C[0])
		ax.set_ylim(-20, 5)
		ax.set_yticks([-20, -10, 0])
		ax.set_yticklabels(['-20', '-10', '0 dBi'], fontsize=8, color=INK2)
		if 'theta' not in title:
			ax.set_theta_zero_location('N')
			ax.set_theta_direction(-1)
		ax.set_title(title, color=INK, fontsize=10, pad=12)
	fig.suptitle('Directivity at 2.44 GHz, matched network (Dmax %.1f dBi), sim axes: x along the board, y towards the antenna edge, z up from F.Cu'
		% D.max(), fontsize=9, color=INK2)
	fig.tight_layout()
	fig.savefig(os.path.join(FIG, 'pattern_cuts.png'))
	plt.close(fig)


def main():
	fin, smoke = load_set(FINAL), load_set(SMOKE)
	refs = {'nomask': load_ref(REF_NOMASK), 'mask': load_ref(REF_MASK)}
	summ = {}
	for nm, m in (('final', fin), ('smoke', smoke)):
		if m is not None:
			summ[nm] = {k: m['json'][k] for k in ('S11_matched_min_dB', 'f_min', 'ble_worst_dB', 'ble_best_dB', 'eff',
				'reciprocity_max_abs_Sij_minus_Sji_2.3_2.6GHz')}
	fig_s11(fin, smoke, refs, summ)
	fig_smith(fin if fin is not None else smoke, refs)
	main_set = fin if fin is not None else smoke
	if main_set is not None:
		fig_budget(main_set, summ)
		fig_tolerance(main_set, summ)
		if main_set['pattern'] is not None:
			fig_pattern(main_set)
	json.dump(summ, open(os.path.join(HERE, 'data', 'summary.json'), 'w'), indent=1)
	print(json.dumps(summ, indent=1)[:3000])


if __name__ == '__main__':
	main()

"""Figures and data tables for the C23 rev B antenna write-up (README.md in this folder).

Reads the openEMS results in ../sim/results/runs/ (pulled with ../sim/sim.sh pull) and writes figures/ and data/.
Nothing here runs a simulation.

Runs used (all on the b3 board export, CR2032 fitted):
    RUN_1P     1-port at J2, L2 0R, L3 open, 20 um mask, fine mesh: antenna impedance, pattern, radiation efficiency
    RUN_3P     3-port J2 / L2 gap / L3 pads, 20 um mask, fine mesh: matching with real part positions (cascade below)
    RUN_PARTS  1-port at J2 with L2 and L3 as lumped series R-L parts in the FDTD model, normal mesh, no mask,
               150 mm air (full-wave check of the cascade, matched pattern), also the run with the field dumps.
               The planned fine-mesh + mask run with the parts (29f9f0e89f) was unstable (energy grew after the
               pulse) and was stopped. Without the mask the response sits about 15-20 MHz higher.

Usage:  python make_figures.py
"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.normpath(os.path.join(HERE, '..', 'sim'))
RUNS = os.path.join(SIM, 'results', 'runs')
sys.path.insert(0, SIM)
import antenna as ant  # noqa: E402

FIG = os.path.join(HERE, 'figures')
DATA = os.path.join(HERE, 'data')
os.makedirs(FIG, exist_ok=True)
os.makedirs(DATA, exist_ok=True)

# b3 = the board as ordered (rounded tracks, AE1 footprint copper used directly, "antenna": "placed")
RUN_1P = 'd349ba0674'
RUN_3P = '819dfacd2e'
RUN_PARTS = '8b668025c7'
BOARD = os.path.join(SIM, 'build', 'b3', 'board.json')
BLE = (2.400e9, 2.4835e9)
FMARK = [2.40e9, 2.44e9, 2.48e9]
# chosen parts and their Q near 2.44 GHz from Murata's website / datasheet data (pim.murata.com, 2026-11-05),
# typical values for the part type, not measured on our parts:
#   L2 Q 106 at 2.41 GHz (Murata Q-frequency data)
#   L3 Q 74 at 2.42 GHz (Murata S-parameter file for the part: Z = 1.38 + 101.7j ohm, 6.69 nH there)
# (before 2026-11-05 assumed Q 25 and 45, the distributor data gives Q only at 250 MHz)
PARTS = {'L2': {'L': 1.6e-9, 'Q': 106, 'pn': 'Murata LQG15WZ1N6B02D', 'tol': 0.1e-9},
	'L3': {'L': 6.8e-9, 'Q': 74, 'pn': 'Murata LQW15AN6N8G80D', 'tol': 0.02 * 6.8e-9}}
# Uncertainty budget for the expected measurement range on the Smith chart (assumed, wider than the tolerance
# section on purpose). shift: whole response moved in frequency, for FR4 er, prepreg/core thickness, copper
# width after etching, solder mask and the model itself (er +-5 % alone gives about +-1 %). L2: part tolerance
# 0.1 nH (6 %) plus pads, solder and placement, 19 % is about 0.3 nH. L3: part tolerance 2 % plus the same.
# Q_factor: part Q down to 70 %. All relative, so the chart title uses % only.
UNC = {'shift': 0.02, 'L2': 0.19, 'L3': 0.05, 'Q_factor': (0.7, 1.0)}
EFF_CAL = 1.089         # own far-field transform with the CR2032 model reads 108.9 % on a lossless case (../sim/archive.py)
Z0 = 50.0

plt.rcParams.update({'font.size': 9, 'axes.grid': True, 'grid.alpha': 0.3, 'savefig.dpi': 200,
	'savefig.bbox': 'tight'})
C_NONE, C_MATCH, C_FW, C_TOL = '#7f7f7f', '#1f5fbf', '#d0402a', '#9ab8e6'


# ---------------------------------------------------------------- data

def read_s11(run):
	d = np.loadtxt(os.path.join(RUNS, run, 'S11.csv'), delimiter=',', skiprows=1)
	return d[:, 0], d[:, 1] + 1j * d[:, 2]


def read_snp(path):
	names, vals = None, []
	for line in open(path):
		if line.startswith('!') and 'ports' in line:
			names = line.split('ports', 1)[1].split()
		line = line.split('!')[0].strip()
		if line and not line.startswith('#'):
			vals += [float(v) for v in line.split()]
	n = len(names)
	v = np.array(vals).reshape(-1, 1 + 2 * n * n)
	S = (v[:, 1::2] + 1j * v[:, 2::2]).reshape(-1, n, n)
	return v[:, 0], S, names


def z_part(L, Q, f):
	return 1j * 2 * np.pi * f * L + 2 * np.pi * 2.44e9 * L / Q


def cascade(f, S, zl2, zl3):
	"""J2 reflection and the power split with the parts fitted on the L2 and L3 ports.
	Returns gin, fraction of incident power into the parts (each) and into the board/antenna."""
	G = np.stack([(zl2 - Z0) / (zl2 + Z0), (zl3 - Z0) / (zl3 + Z0)], axis=1)
	S11, S1x, Sx1, Sxx = S[:, 0, 0], S[:, 0, 1:], S[:, 1:, 0], S[:, 1:, 1:]
	gin, ploss = np.zeros(len(f), complex), np.zeros((len(f), 2))
	for k in range(len(f)):
		Gd = np.diag(G[k])
		bx = np.linalg.solve(np.eye(2) - Sxx[k] @ Gd, Sx1[k])      # waves leaving the board into the parts
		ax = Gd @ bx
		gin[k] = S11[k] + S1x[k] @ ax
		ploss[k] = np.abs(bx) ** 2 - np.abs(ax) ** 2
	pacc = 1 - np.abs(gin) ** 2
	return gin, ploss, pacc - ploss.sum(axis=1)


def shift(f, S, s):
	"""Move the whole response by a factor 1 + s in frequency (resonance tolerance estimate)."""
	out = np.empty_like(S)
	for i in range(S.shape[1]):
		for j in range(S.shape[2]):
			out[:, i, j] = np.interp(f, f * (1 + s), S[:, i, j].real) + 1j * np.interp(f, f * (1 + s), S[:, i, j].imag)
	return out


def dB(g):
	return 20 * np.log10(np.abs(g))


def ble(f):
	return (f >= BLE[0]) & (f <= BLE[1])


def shade(ax):
	ax.axvspan(BLE[0] / 1e9, BLE[1] / 1e9, color='#2ca02c', alpha=0.12, lw=0, label='BLE 2400-2483.5 MHz')


f1, g1 = read_s11(RUN_1P)
r1 = json.load(open(os.path.join(RUNS, RUN_1P, 'result.json')))
f3, S3, names3 = read_snp(os.path.join(RUNS, RUN_3P, 'S3P.s3p'))
zL2 = z_part(PARTS['L2']['L'], PARTS['L2']['Q'], f3)
zL3 = z_part(PARTS['L3']['L'], PARTS['L3']['Q'], f3)
gm, pl, pboard = cascade(f3, S3, zL2, zL3)
g_open, _, _ = cascade(f3, S3, np.full(len(f3), 1e-6 + 0j), np.full(len(f3), 1e9 + 0j))     # L2 0R, L3 open
fw = None
if RUN_PARTS and os.path.exists(os.path.join(RUNS, RUN_PARTS, 'S11.csv')):
	fw = read_s11(RUN_PARTS)
	rp = json.load(open(os.path.join(RUNS, RUN_PARTS, 'result.json')))


# ---------------------------------------------------------------- geometry

def kc(x, y):
	return np.asarray(x) + 150.0, 100.0 - np.asarray(y)


def dim(ax, p0, p1, text, off=(0, 0), fs=7, color='k', ha='center', va='center'):
	ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle='<|-|>', mutation_scale=7, lw=0.7, color=color, shrinkA=0, shrinkB=0))
	ax.text((p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1], text, fontsize=fs, ha=ha, va=va, color=color,
		bbox=dict(fc='white', ec='none', alpha=0.8, pad=0.5))


def draw_board(ax, board, zoom):
	for o in board['outline']:
		x, y = kc(*np.array(o).T)
		ax.add_patch(Polygon(np.c_[x, y], fc='#2e6b3a', ec='k', lw=1.0, alpha=0.18))
	for pts in board['copper']['F.Cu']:
		x, y = kc(*np.array(pts).T)
		ax.add_patch(Polygon(np.c_[x, y], fc='#c87533', ec='none', alpha=0.55))
	for v in board['vias']:
		x, y = kc(v['x'], v['y'])
		ax.add_patch(plt.Circle((x, y), v['drill'] / 2, fc='k', lw=0))
	for pts in board['ae1']['copper']:
		x, y = kc(*np.array(pts).T)
		ax.add_patch(Polygon(np.c_[x, y], fc='#2f5fd0', ec='#123', lw=0.5))
	for ref, col in (('J2', '#c02cc0'), ('L2', '#2ca02c'), ('L3', '#2ca02c')):
		for p in board['pads'][ref]['pads']:
			x0, y0, x1, y1 = p['bbox']
			(a, b), (c, d) = kc(x0, y0), kc(x1, y1)
			ax.add_patch(Rectangle((a, d), c - a, b - d, fc=col, ec='none', alpha=0.9 if (ref != 'J2' or p['num'] == '1') else 0.35))
	ax.set_aspect('equal')
	ax.tick_params(labelsize=7)


def fig_geometry():
	board = json.load(open(BOARD))
	fig, ax = plt.subplots(figsize=(9, 4.6))
	draw_board(ax, board, True)
	ax.set_xlim(132, 168)
	ax.set_ylim(95, 81.5)
	ax.set_xlabel('KiCad x (mm)')
	ax.set_ylabel('KiCad y (mm)')
	# dimensions (KiCad coordinates)
	gy, ay0, ay1 = 90.4, 85.4, 84.4
	dim(ax, (160.0, gy), (160.0, ay0), 'H 5.0', off=(1.2, 0))
	dim(ax, (139.6, 83.2), (159.0, 83.2), 'arm 139.6 .. 159.0 (19.4 mm)')
	dim(ax, (161.5, ay1), (161.5, ay0), 'Wa 1.0', off=(1.5, 0))
	dim(ax, (140.6, 87.6), (144.1, 87.6), 'S 3.5', off=(0, -0.55))
	dim(ax, (139.6, 89.0), (141.6, 89.0), 'Ws 2', off=(0, 0.6))
	dim(ax, (143.6, 89.0), (144.6, 89.0), 'Wf 1', off=(0, 0.6))
	dim(ax, (159.0, 84.9), (159.75, 84.9), '', fs=6)
	ax.annotate('0.75 mm to the board edge', (159.4, 84.9), (163.5, 82.4), fontsize=7, arrowprops=dict(arrowstyle='-', lw=0.5))
	ax.annotate('ground edge y 90.4\n(all four layers)', (152, 90.4), (150, 93.5), fontsize=7, arrowprops=dict(arrowstyle='-', lw=0.5))
	ax.annotate('feed notch, AE1 pad 1\nfeed trace from L2/L3', (144.1, 91.0), (133, 93.6), fontsize=7, arrowprops=dict(arrowstyle='-', lw=0.5))
	ax.annotate('short leg to ground', (140.6, 88.0), (133, 86.0), fontsize=7, arrowprops=dict(arrowstyle='-', lw=0.5))
	ax.set_title('C23 rev B inverted-F antenna (AE1, footprint IFA_2G4). Blue antenna, brown F.Cu ground, '
		'green L2/L3 pads, magenta J2', fontsize=8)
	fig.savefig(os.path.join(FIG, 'antenna_dimensions.png'))
	plt.close(fig)

	fig, ax = plt.subplots(figsize=(5.6, 5.6))
	draw_board(ax, board, False)
	bx, by = kc(*board['pads']['BT1']['pos'])
	ax.add_patch(plt.Circle((bx, by), 10, fc='none', ec='#555', ls='--', lw=0.8))
	ax.text(bx, by + 6.5, 'CR2032 under B.Cu\n(modelled as metal)', ha='center', fontsize=7, color='#444')
	ax.set_xlim(131, 169)
	ax.set_ylim(119, 81)
	ax.set_xlabel('KiCad x (mm)')
	ax.set_ylabel('KiCad y (mm)')
	ax.set_title('Board 34 x 34 mm, R10 corners, antenna along the top edge', fontsize=8)
	fig.savefig(os.path.join(FIG, 'board_overview.png'))
	plt.close(fig)

	# stack-up cross-section (not to scale in x)
	st = board['stackup']
	fig, ax = plt.subplots(figsize=(6, 2.6))
	for d in st['dielectrics']:
		ax.add_patch(Rectangle((0, d['z0']), 10, d['z1'] - d['z0'], fc='#e8d9a8' if d['z1'] - d['z0'] < 0.5 else '#d8c27a', ec='none'))
		ax.text(10.3, (d['z0'] + d['z1']) / 2, '%s  %.3f mm, er %.2f, tan d %.2f' % (d['name'], d['z1'] - d['z0'], d['er'], d['tand']),
			va='center', fontsize=7)
	for n, c in st['copper'].items():
		ax.plot([0, 10], [c['z'], c['z']], color='#c87533', lw=2.5)
		ax.text(-0.3, c['z'], '%s  z %.3f' % (n, c['z']), ha='right', va='center', fontsize=7)
	ax.set_xlim(-6, 24)
	ax.set_ylim(-0.15, 1.65)
	ax.axis('off')
	ax.set_title('JLC 4-layer stack-up as modelled (copper as zero-thickness metal sheets, plus 20 um mask er 3.8 on both sides)', fontsize=7)
	fig.savefig(os.path.join(FIG, 'stackup.png'))
	plt.close(fig)


# ---------------------------------------------------------------- S11, Smith

def fig_s11():
	fig, ax = plt.subplots(figsize=(7, 4))
	shade(ax)
	ax.plot(f3 / 1e9, dB(g_open), color=C_NONE, label='no parts (L2 0R, L3 open)')
	lo, hi = [], []
	for s in (-0.01, 0.01):
		g, _, _ = cascade(f3, shift(f3, S3, s), zL2, zL3)
		lo.append(dB(g))
	ax.fill_between(f3 / 1e9, np.minimum(*lo), np.maximum(*lo), color=C_TOL, alpha=0.45, lw=0, label='resonance shifted +-1 %')
	ax.plot(f3 / 1e9, dB(gm), color=C_MATCH, lw=1.8, label='L2 1.6 nH, L3 6.8 nH (3-port + part models)')
	if fw is not None:
		ax.plot(fw[0] / 1e9, dB(fw[1]), color=C_FW, ls='--', lw=1.3, label='L2, L3 as lumped parts in the FDTD run (no mask, normal mesh)')
	ax.axhline(-10, color='k', lw=0.6, ls=':')
	ax.set_xlim(2.0, 2.9)
	ax.set_ylim(-35, 0)
	ax.set_xlabel('frequency (GHz)')
	ax.set_ylabel('|S11| at J2 (dB)')
	ax.legend(fontsize=7, loc='lower left')
	ax.set_title('Reflection at J2 (50 ohm), simulated', fontsize=9)
	fig.savefig(os.path.join(FIG, 's11.png'))
	plt.close(fig)

	# VSWR
	fig, ax = plt.subplots(figsize=(7, 3))
	shade(ax)
	vs = lambda g: (1 + np.abs(g)) / (1 - np.abs(g))
	ax.plot(f3 / 1e9, vs(gm), color=C_MATCH, lw=1.8, label='L2 1.6 nH, L3 6.8 nH')
	if fw is not None:
		ax.plot(fw[0] / 1e9, vs(fw[1]), color=C_FW, ls='--', label='lumped parts in the FDTD run (no mask)')
	ax.plot(f3 / 1e9, vs(g_open), color=C_NONE, label='no parts')
	ax.set_xlim(2.2, 2.7)
	ax.set_ylim(1, 5)
	ax.set_xlabel('frequency (GHz)')
	ax.set_ylabel('VSWR')
	ax.legend(fontsize=7)
	fig.savefig(os.path.join(FIG, 'vswr.png'))
	plt.close(fig)

	# impedance at J2 without parts
	Z = Z0 * (1 + g1) / (1 - g1)
	fig, ax = plt.subplots(figsize=(7, 3.4))
	shade(ax)
	ax.plot(f1 / 1e9, Z.real, label='R')
	ax.plot(f1 / 1e9, Z.imag, label='X')
	ax.axhline(50, color='k', lw=0.6, ls=':')
	ax.axhline(0, color='k', lw=0.6)
	ax.set_xlim(2.1, 2.9)
	ax.set_ylim(-150, 150)
	ax.set_xlabel('frequency (GHz)')
	ax.set_ylabel('Z at J2, no parts (ohm)')
	ax.legend(fontsize=7)
	ax.set_title('Antenna impedance at J2 with L2 0R and L3 open (includes the 50 ohm feed trace from AE1 to J2)', fontsize=8)
	fig.savefig(os.path.join(FIG, 'impedance.png'))
	plt.close(fig)


def smith_grid(ax):
	t = np.linspace(0, 2 * np.pi, 400)
	ax.plot(np.cos(t), np.sin(t), color='k', lw=0.8)
	for r in (0.2, 0.5, 1, 2, 5):
		c, rad = r / (1 + r), 1 / (1 + r)
		ax.plot(c + rad * np.cos(t), rad * np.sin(t), color='#bbb', lw=0.5)
		ax.text(c - rad + 0.01, 0.02, '%g' % r, fontsize=6, color='#888', clip_on=True)
	for x in (0.2, 0.5, 1, 2, 5):
		for s in (1, -1):
			z = 1j * s * x + np.concatenate([[0], np.geomspace(1e-3, 50, 400)])
			g = (z - 1) / (z + 1)
			ax.plot(g.real, g.imag, color='#bbb', lw=0.5)
		g = (1j * x - 1) / (1j * x + 1)
		ax.text(g.real * 1.06, g.imag * 1.06, '%gj' % x, fontsize=6, color='#888', ha='center', va='center', clip_on=True)
		ax.text(g.real * 1.06, -g.imag * 1.06, '-%gj' % x, fontsize=6, color='#888', ha='center', va='center', clip_on=True)
	ax.plot([-1, 1], [0, 0], color='#bbb', lw=0.5)
	ax.set_xlim(-1.12, 1.12)
	ax.set_ylim(-1.12, 1.12)
	ax.set_aspect('equal')
	ax.axis('off')


def smith_trace(ax, f, g, color, label, lw=1.2, ls='-', markers=True):
	sel = (f >= 2.2e9) & (f <= 2.7e9)
	ax.plot(g[sel].real, g[sel].imag, color=color, lw=0.7, ls=ls, alpha=0.6)
	b = ble(f)
	ax.plot(g[b].real, g[b].imag, color=color, lw=lw * 2.2, ls=ls, label=label)
	if markers:
		for fm, mk in zip(FMARK, ('o', 's', '^')):
			k = int(np.argmin(np.abs(f - fm)))
			ax.plot(g[k].real, g[k].imag, mk, color=color, ms=4, mfc='white')


def hull(p):
	"""Convex hull of 2D points (monotone chain), closed polygon."""
	p = p[np.lexsort((p[:, 1], p[:, 0]))]
	def half(q):
		h = []
		for x in q:
			while len(h) >= 2 and ((h[-1][0] - h[-2][0]) * (x[1] - h[-2][1])
					- (h[-1][1] - h[-2][1]) * (x[0] - h[-2][0])) <= 0:
				h.pop()
			h.append(x)
		return h[:-1]
	h = half(p) + half(p[::-1])
	return np.array(h + [h[0]])


def fig_smith():
	fig, axs = plt.subplots(1, 2, figsize=(10, 5))
	for ax in axs:
		smith_grid(ax)
	ax = axs[0]
	smith_trace(ax, f1, g1, C_NONE, 'no parts (1-port run)')
	# matching steps: L3 alone, then L2 added
	g_l3, _, _ = cascade(f3, S3, np.full(len(f3), 1e-6 + 0j), zL3)
	smith_trace(ax, f3, g_l3, '#e08a1e', 'L3 6.8 nH only')
	smith_trace(ax, f3, gm, C_MATCH, 'L2 1.6 nH + L3 6.8 nH')
	ax.legend(fontsize=7, loc='lower left', bbox_to_anchor=(-0.05, -0.08))
	ax.set_title('2.2-2.7 GHz (thick: BLE band)', fontsize=8)
	ax = axs[1]
	t = np.linspace(0, 2 * np.pi, 200)
	r = 10 ** (-10 / 20)
	ax.plot(r * np.cos(t), r * np.sin(t), 'k:', lw=0.7, label='|S11| = -10 dB')
	# expected measurement range: every combination of the UNC budget, region = union of the per-frequency hulls
	sel = (f3 >= BLE[0] - 1e-3) & (f3 <= BLE[1] + 1e-3)
	idx = np.flatnonzero(sel)[::5]
	pts = []
	for s in np.linspace(-UNC['shift'], UNC['shift'], 9):
		S = shift(f3, S3, s) if s else S3
		for d2 in (-1, 0, 1):
			for d3 in (-1, 0, 1):
				for qf in UNC['Q_factor']:
					L2 = PARTS['L2']['L'] * (1 + d2 * UNC['L2'])
					L3 = PARTS['L3']['L'] * (1 + d3 * UNC['L3'])
					g, _, _ = cascade(f3, S, z_part(L2, PARTS['L2']['Q'] * qf, f3), z_part(L3, PARTS['L3']['Q'] * qf, f3))
					pts.append(g[idx])
	pts = np.array(pts)                       # (cases, freqs)
	unc_worst = dB(pts).max()
	for k in range(pts.shape[1]):
		h = hull(np.column_stack([pts[:, k].real, pts[:, k].imag]))
		ax.fill(h[:, 0], h[:, 1], color='#c9d9f2', lw=0)
	ax.fill([], [], color='#c9d9f2', label='expected range, BLE band')
	smith_trace(ax, f3, gm, C_MATCH, 'nominal: L2 1.6 nH, L3 6.8 nH')
	m = max(np.abs(pts.real).max(), np.abs(pts.imag).max(), r) * 1.12
	ax.set_xlim(-m, m)
	ax.set_ylim(-m, m)
	ax.legend(fontsize=7, loc='lower left')
	ax.set_title('Matched, zoom. Range: L2 ±%g %%, L3 ±%g %%, part Q −%g %%,\nresponse shifted ±%g %% in frequency'
		% (UNC['L2'] * 100, UNC['L3'] * 100, (1 - min(UNC['Q_factor'])) * 100, UNC['shift'] * 100), fontsize=8)
	print('expected range: worst BLE S11 over all cases %.1f dB' % unc_worst)
	fig.suptitle('S11 @ J2, markers at 2.40, 2.44, 2.48 GHz (circle, square, triangle)', fontsize=10)
	fig.savefig(os.path.join(FIG, 'smith.png'))
	plt.close(fig)


# ---------------------------------------------------------------- tolerance

def tolerance():
	rows = []
	b = ble(f3)
	for s in (-0.01, -0.005, 0.0, 0.005, 0.01):
		S = shift(f3, S3, s) if s else S3
		for d2 in (-1, 0, 1):
			for d3 in (-1, 0, 1):
				L2 = PARTS['L2']['L'] + d2 * PARTS['L2']['tol']
				L3 = PARTS['L3']['L'] + d3 * PARTS['L3']['tol']
				g, _, _ = cascade(f3, S, z_part(L2, PARTS['L2']['Q'], f3), z_part(L3, PARTS['L3']['Q'], f3))
				rows.append((s, L2, L3, dB(g[b]).max()))
	rows = np.array(rows)
	np.savetxt(os.path.join(DATA, 'tolerance.csv'), rows, delimiter=',', fmt='%.6g',
		header='resonance_shift,L2_H,L3_H,worst_BLE_S11_dB', comments='')
	fig, ax = plt.subplots(figsize=(6, 3.2))
	for s in np.unique(rows[:, 0]):
		r = rows[rows[:, 0] == s]
		ax.plot([s * 100] * len(r), r[:, 3], 'o', color=C_TOL, ms=4)
		nom = r[(np.isclose(r[:, 1], PARTS['L2']['L'])) & (np.isclose(r[:, 2], PARTS['L3']['L']))][0, 3]
		ax.plot(s * 100, nom, 'o', color=C_MATCH, ms=6)
	ax.axhline(-10, color='k', lw=0.6, ls=':')
	ax.set_xlabel('resonance shift (%), about 26 MHz per %')
	ax.set_ylabel('worst BLE channel |S11| (dB)')
	ax.set_title('Blue: nominal parts. Light: L2 +-0.1 nH and L3 +-2 % corners', fontsize=8)
	fig.savefig(os.path.join(FIG, 'tolerance.png'))
	plt.close(fig)
	return rows


# ---------------------------------------------------------------- pattern

def load_pattern(run):
	d = np.load(os.path.join(RUNS, run, 'pattern.npz'))
	return d['f'], d['theta'], d['phi'], d['D_dBi']


def fig_pattern(run, eff, tag, title):
	f, th, ph, D = load_pattern(run)
	k = int(np.argmin(np.abs(f - 2.44e9)))
	Dk = D[k]
	erad = eff[k]['rad_eff'] / EFF_CAL
	G = Dk + 10 * np.log10(erad)
	# cuts: XY (theta 90, phi 0..360), XZ (phi 0 / 180), YZ (phi 90 / 270)
	def cut_phi(p):
		a = Dk[:, list(ph).index(p)]
		b = Dk[:, list(ph).index((p + 180) % 360)]
		ang = np.concatenate([th, 360 - th[::-1]])
		return np.radians(ang), np.concatenate([a, b[::-1]])
	fig, axs = plt.subplots(1, 3, subplot_kw={'projection': 'polar'}, figsize=(12, 4.3))
	cuts = [('XY plane (board plane), theta 90', np.radians(ph), Dk[list(th).index(90), :], 'phi'),
		('XZ plane (along the arm), phi 0/180', *cut_phi(0), 'theta'),
		('YZ plane (across the arm), phi 90/270', *cut_phi(90), 'theta')]
	for ax, (name, a, v, lab) in zip(axs, cuts):
		ax.plot(a, v, color=C_MATCH, lw=1.6, label='directivity')
		ax.plot(a, v + 10 * np.log10(erad), color=C_FW, lw=1.0, ls='--', label='gain (rad. eff. %.0f %%)' % (erad * 100))
		ax.set_rlim(-15, 5)
		ax.set_rticks([-15, -10, -5, 0, 5])
		ax.set_rlabel_position(135)
		ax.tick_params(labelsize=7)
		if lab == 'theta':
			ax.set_theta_zero_location('N')
			ax.set_theta_direction(-1)
		ax.set_title(name, fontsize=8)
	axs[0].legend(fontsize=7, loc='lower left', bbox_to_anchor=(-0.25, -0.2))
	fig.suptitle('%s, 2.44 GHz, dBi. x along the board top edge (arm direction), y up the board, z out of the '
		'component side (F.Cu)' % title, fontsize=8)
	fig.savefig(os.path.join(FIG, 'pattern_cuts%s.png' % tag))
	plt.close(fig)

	# map
	fig, ax = plt.subplots(figsize=(7, 3.6))
	m = ax.pcolormesh(ph, th, Dk, shading='auto', cmap='viridis', vmin=-10, vmax=3)
	fig.colorbar(m, ax=ax, label='directivity (dBi)')
	ax.set_xlabel('phi (deg), 0 = +x')
	ax.set_ylabel('theta (deg), 0 = +z')
	ax.set_title('Directivity at 2.44 GHz, Dmax %.1f dBi' % Dk.max(), fontsize=8)
	fig.savefig(os.path.join(FIG, 'pattern_map%s.png' % tag))
	plt.close(fig)

	# 3D
	T, P = np.meshgrid(np.radians(th), np.radians(ph), indexing='ij')
	r = np.clip(Dk + 10, 0, None)                                # dB scale from -10 dBi
	X, Y, Zs = r * np.sin(T) * np.cos(P), r * np.sin(T) * np.sin(P), r * np.cos(T)
	fig = plt.figure(figsize=(6.5, 6))
	ax = fig.add_subplot(projection='3d')
	norm = plt.Normalize(-8, Dk.max())
	ax.plot_surface(X, Y, Zs, facecolors=plt.cm.viridis(norm(Dk)), rstride=1, cstride=1, linewidth=0.1,
		edgecolor=(0, 0, 0, 0.15), antialiased=True, shade=False, alpha=0.9)
	for v, lab in (((14, 0, 0), '+x'), ((0, 14, 0), '+y'), ((0, 0, 14), '+z')):
		ax.plot([0, v[0]], [0, v[1]], [0, v[2]], 'k-', lw=0.6)
		ax.text(*[c * 1.05 for c in v], lab, fontsize=8)
	lim = 11
	ax.set_xlim(-lim, lim)
	ax.set_ylim(-lim, lim)
	ax.set_zlim(-lim, lim)
	ax.set_box_aspect((1, 1, 1))
	ax.set_axis_off()
	ax.view_init(elev=25, azim=-60)
	ax.set_title('3D directivity at 2.44 GHz (radius = linear directivity)\nblack: board outline, red: antenna arm (symbols, not to scale)', fontsize=8)
	sm = plt.cm.ScalarMappable(cmap='viridis', norm=norm)
	fig.colorbar(sm, ax=ax, shrink=0.6, label='directivity (dBi)')
	fig.savefig(os.path.join(FIG, 'pattern_3d%s.png' % tag))
	plt.close(fig)

	# data
	tt, pp = np.meshgrid(th, ph, indexing='ij')
	np.savetxt(os.path.join(DATA, 'pattern_2440MHz%s.csv' % tag), np.c_[tt.ravel(), pp.ravel(), Dk.ravel(), G.ravel()],
		delimiter=',', fmt='%.4g', header='theta_deg,phi_deg,directivity_dBi,gain_dBi', comments='')
	return Dk


# ---------------------------------------------------------------- efficiency budget

def efficiency():
	eff1 = r1['eff']
	rows = []
	for e in eff1:
		fk = e['f']
		k = int(np.argmin(np.abs(f3 - fk)))
		erad = e['rad_eff'] / EFF_CAL
		mism = 1 - abs(gm[k]) ** 2
		pparts = pl[k]
		into_board = pboard[k]
		tot = into_board * erad
		row = {'f_GHz': fk / 1e9, 'S11_dB': float(dB(gm[k])), 'mismatch_frac': float(mism),
			'L2_loss_frac': float(pparts[0]), 'L3_loss_frac': float(pparts[1]), 'into_board_frac': float(into_board),
			'board_rad_eff': float(erad), 'total_eff': float(tot), 'total_eff_dB': float(10 * np.log10(tot)),
			'Dmax_dBi': e['Dmax_dBi'], 'peak_realised_gain_dBi': float(e['Dmax_dBi'] + 10 * np.log10(tot)),
			'rad_eff_raw': e['rad_eff']}
		if fw is not None and rp.get('eff'):
			ep = rp['eff'][[x['f'] for x in rp['eff']].index(fk)]
			row['fdtd_parts_rad_eff'] = ep['rad_eff'] / EFF_CAL         # Prad / accepted at J2, part loss included
			row['fdtd_parts_tot_eff'] = ep['tot_eff'] / EFF_CAL
			row['fdtd_parts_Dmax_dBi'] = ep['Dmax_dBi']
		rows.append(row)
	json.dump(rows, open(os.path.join(DATA, 'efficiency.json'), 'w'), indent=1)
	keys = list(rows[0].keys())
	with open(os.path.join(DATA, 'efficiency.csv'), 'w') as fh:
		fh.write(','.join(keys) + '\n')
		for r in rows:
			fh.write(','.join('%.5g' % r[k] for k in keys) + '\n')
	# loss budget figure (dB)
	fig, ax = plt.subplots(figsize=(6.5, 3))
	lab = ['%.2f GHz' % r['f_GHz'] for r in rows]
	parts = [('mismatch', [-10 * np.log10(r['mismatch_frac']) for r in rows], '#bbb'),
		('L2 + L3 loss', [-10 * np.log10(r['into_board_frac'] / r['mismatch_frac']) for r in rows], '#e08a1e'),
		('board loss (FR4, copper model PEC)', [-10 * np.log10(r['board_rad_eff']) for r in rows], C_MATCH)]
	left = np.zeros(len(rows))
	for n, v, c in parts:
		ax.barh(lab, v, left=left, color=c, label=n)
		left += np.array(v)
	for i, l in enumerate(left):
		ax.text(l + 0.03, i, '%.2f dB (%.0f %%)' % (l, 100 * 10 ** (-l / 10)), va='center', fontsize=7)
	ax.set_xlim(0, max(left) * 1.6)
	ax.set_xlabel('loss from the 50 ohm source at J2 to radiated power (dB)')
	ax.legend(fontsize=7, loc='lower center', bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False)
	fig.savefig(os.path.join(FIG, 'efficiency_budget.png'))
	plt.close(fig)
	return rows


def export_curves():
	Zm = Z0 * (1 + gm) / (1 - gm)
	np.savetxt(os.path.join(DATA, 's11_matched_cascade.csv'),
		np.c_[f3, gm.real, gm.imag, dB(gm), Zm.real, Zm.imag, pl[:, 0], pl[:, 1], pboard],
		delimiter=',', fmt='%.6g', comments='',
		header='f_Hz,S11_re,S11_im,S11_dB,Zin_re_ohm,Zin_im_ohm,L2_loss_frac,L3_loss_frac,into_board_frac')
	Z = Z0 * (1 + g1) / (1 - g1)
	np.savetxt(os.path.join(DATA, 's11_no_parts.csv'), np.c_[f1, g1.real, g1.imag, dB(g1), Z.real, Z.imag],
		delimiter=',', fmt='%.6g', comments='', header='f_Hz,S11_re,S11_im,S11_dB,Zin_re_ohm,Zin_im_ohm')
	import shutil
	shutil.copy(os.path.join(RUNS, RUN_3P, 'S3P.s3p'), os.path.join(DATA, 'board_J2_L2_L3.s3p'))
	if fw is not None:
		shutil.copy(os.path.join(RUNS, RUN_PARTS, 'S11.csv'), os.path.join(DATA, 's11_matched_fdtd.csv'))


def summary(tol, eff_rows):
	b = ble(f3)
	out = {'runs': {'one_port': RUN_1P, 'three_port': RUN_3P, 'parts_fdtd': RUN_PARTS or None},
		'antenna': 'AE1 copper from build/b3/board.json (IFA S 3.5, Ws 2, Wf 1, H 5.0, Wa 1, arm to KiCad x 159.0)', 'parts': {k: {kk: v for kk, v in p.items()} for k, p in PARTS.items()},
		'no_parts': {'f_res_GHz': float(f1[np.argmin(dB(g1))] / 1e9), 'S11_min_dB': float(dB(g1).min()),
			'worst_BLE_dB': float(dB(g1[ble(f1)]).max())},
		'matched_cascade': {'worst_BLE_dB': float(dB(gm[b]).max()), 'best_BLE_dB': float(dB(gm[b]).min()),
			'f_min_GHz': float(f3[np.argmin(dB(gm))] / 1e9), 'S11_min_dB': float(dB(gm).min())},
		'tolerance_worst_BLE_dB': {('%+.1f%%' % (s * 100)): [float(tol[tol[:, 0] == s][:, 3].min()), float(tol[tol[:, 0] == s][:, 3].max())]
			for s in np.unique(tol[:, 0])},
		'efficiency': eff_rows}
	sel = dB(gm) < -10
	idx = np.where(sel)[0]
	if len(idx):
		# contiguous band around the minimum
		k = int(np.argmin(dB(gm)))
		lo, hi = k, k
		while lo > 0 and sel[lo - 1]:
			lo -= 1
		while hi < len(f3) - 1 and sel[hi + 1]:
			hi += 1
		out['matched_cascade']['bw10_MHz'] = [float(f3[lo] / 1e6), float(f3[hi] / 1e6)]
	if fw is not None:
		ff, gg = fw
		out['matched_fdtd'] = {'worst_BLE_dB': float(dB(gg[ble(ff)]).max()), 'f_min_GHz': float(ff[np.argmin(dB(gg))] / 1e9),
			'S11_min_dB': float(dB(gg).min())}
	json.dump(out, open(os.path.join(DATA, 'summary.json'), 'w'), indent=1)
	print(json.dumps({k: v for k, v in out.items() if k != 'efficiency'}, indent=1))
	for r in eff_rows:
		print(r)


if __name__ == '__main__':
	fig_geometry()
	fig_s11()
	fig_smith()
	tol = tolerance()
	fig_pattern(RUN_1P, r1['eff'], '', 'No parts (1-port run)')
	if fw is not None and rp.get('eff'):
		fig_pattern(RUN_PARTS, rp['eff'], '_matched', 'L2 1.6 nH + L3 6.8 nH in the FDTD run')
	rows = efficiency()
	export_curves()
	summary(tol, rows)

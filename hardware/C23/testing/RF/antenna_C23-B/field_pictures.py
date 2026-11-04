"""Still pictures and GIFs of the fields from the detailed run (matplotlib, no ParaView needed).

Reads the 2.44 GHz phasor dumps (fd_*.h5) and the time-domain samples (td_*.vtr) of the run's sim_e0 folder and
writes figures/fields/. Field values are relative (the source is the openEMS excitation, not a set power). Magnitude pictures are in dB
with 0 dB at the 99.5th percentile of the picture, the GIFs show one field component normalised to its maximum.

Usage:  python field_pictures.py <sim_e0 dir>
"""
import json
import os
import sys

import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Polygon, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.normpath(os.path.join(HERE, '..', 'sim'))
sys.path.insert(0, SIM)
import antenna as ant  # noqa: E402

ANT = {'family': 'ifa', 'base': 'b2', 'S': 3.5, 'Ws': 2.0, 'Wf': 1.0, 'H': 5.0, 'Wa': 1.0, 'L': 9.0}
BOARD = json.load(open(os.path.join(SIM, 'build', 'b2', 'board.json')))
OUT = os.path.join(HERE, 'figures', 'fields')
ZF, ZIN1 = 1.4858, 1.2754
plt.rcParams.update({'font.size': 8, 'savefig.dpi': 170, 'savefig.bbox': 'tight'})


def read_fd(src, name):
	h = h5py.File(os.path.join(src, name + '.h5'), 'r')
	x, y, z = (np.array(h['Mesh'][k], float) * 1e3 for k in 'xyz')
	F = np.array(h['FieldData/FD/f0']).astype(complex)        # (3, nx, ny, nz)
	return x, y, z, F


def overlay_top(ax, lw=0.6, col='w'):
	for o in BOARD['outline']:
		ax.add_patch(Polygon(np.array(o), fill=False, ec=col, lw=lw, ls='--'))
	for pts in BOARD['copper']['F.Cu']:
		ax.add_patch(Polygon(np.array(pts), fill=False, ec=col, lw=lw * 0.6, alpha=0.7))
	for (x0, y0, x1, y1) in ant.rects(ANT)[0]:
		ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec=col, lw=lw))


def overlay_cut_yz(ax, x0, col='w'):
	"""Board section in a plane x = x0: dielectric, copper lines and the antenna (y-z view)."""
	ax.add_patch(Rectangle((-17, 0), 34, ZF, fill=False, ec=col, lw=0.6, ls='--'))
	for (a0, b0, a1, b1) in ant.rects(ANT)[0]:
		if a0 <= x0 <= a1:
			ax.plot([b0, b1], [ZF, ZF], color=col, lw=2.2)
	gy = ant.base(ANT)['GND_Y']
	for z in (0, 0.2104, ZIN1, ZF):
		ax.plot([-17, gy], [z, z], color=col, lw=1.0, alpha=0.8)


def overlay_cut_xz(ax, y0, col='w'):
	ax.add_patch(Rectangle((-17, 0), 34, ZF, fill=False, ec=col, lw=0.6, ls='--'))
	for (a0, b0, a1, b1) in ant.rects(ANT)[0]:
		if b0 <= y0 <= b1:
			ax.plot([a0, a1], [ZF, ZF], color=col, lw=2.2)


REF_PCT = 99.5        # 0 dB = this percentile of the picture, so a few cells at the lumped parts do not set the scale


def db(a, floor=-40):
	a = np.abs(a)
	return np.clip(20 * np.log10(a / np.percentile(a, REF_PCT) + 1e-30), floor, 0)


def plane2d(x, y, z, F):
	"""Drop the singleton axis: returns (u, v, F2 (3, nu, nv), axis names)."""
	n = [len(x), len(y), len(z)]
	k = int(np.argmin(n))
	c = [x, y, z]
	axes = [i for i in range(3) if i != k]
	F2 = np.take(F, 0, axis=1 + k)
	return c[axes[0]], c[axes[1]], F2, axes


def still_magnitude(src, name, title, overlay, xlim, ylim, out, labels, floor=-40):
	x, y, z, F = read_fd(src, name)
	u, v, F2, _ = plane2d(x, y, z, F)
	amp = np.sqrt(np.sum(np.abs(F2) ** 2, axis=0))
	fig, ax = plt.subplots(figsize=(7, 5))
	m = ax.pcolormesh(u, v, db(amp, floor).T, shading='auto', cmap='inferno', vmin=floor, vmax=0)
	overlay(ax)
	ax.set_xlim(*xlim)
	ax.set_ylim(*ylim)
	ax.set_aspect('equal')
	ax.set_xlabel(labels[0])
	ax.set_ylabel(labels[1])
	ax.set_title(title)
	fig.colorbar(m, ax=ax, shrink=0.8, label='dB, 0 dB = %g th percentile of the picture' % REF_PCT)
	fig.savefig(os.path.join(OUT, out))
	plt.close(fig)


def quiver_cut(src, name, title, overlay, xlim, ylim, out, labels, comp, phase=0.0):
	"""Instantaneous field in the plane (arrows, normalised) over the magnitude."""
	x, y, z, F = read_fd(src, name)
	u, v, F2, axes = plane2d(x, y, z, F)
	R = np.real(F2 * np.exp(1j * phase))
	amp = np.sqrt(np.sum(np.abs(F2) ** 2, axis=0))
	fig, ax = plt.subplots(figsize=(7, 4.4))
	m = ax.pcolormesh(u, v, db(amp, -35).T, shading='auto', cmap='inferno', vmin=-35, vmax=0)
	su = (u >= xlim[0]) & (u <= xlim[1])
	sv = (v >= ylim[0]) & (v <= ylim[1])
	U, V = np.meshgrid(u[su], v[sv], indexing='ij')
	A, B = R[axes[0]][np.ix_(su, sv)], R[axes[1]][np.ix_(su, sv)]
	# resample to a regular arrow grid
	gu = np.linspace(xlim[0], xlim[1], 46)
	gv = np.linspace(ylim[0], ylim[1], int(46 * (ylim[1] - ylim[0]) / (xlim[1] - xlim[0])) + 2)
	iu = np.searchsorted(u, gu).clip(0, len(u) - 1)
	iv = np.searchsorted(v, gv).clip(0, len(v) - 1)
	Ga, Gb = R[axes[0]][np.ix_(iu, iv)], R[axes[1]][np.ix_(iu, iv)]
	mag = np.hypot(Ga, Gb) + 1e-30
	L = np.clip(20 * np.log10(mag / mag.max()) + 35, 0, 35) / 35          # arrow length on a log scale
	GU, GV = np.meshgrid(gu, gv, indexing='ij')
	ax.quiver(GU, GV, Ga / mag * L, Gb / mag * L, color='#7fd4ff', scale=40, width=0.0025, headwidth=3.5)
	overlay(ax)
	ax.set_xlim(*xlim)
	ax.set_ylim(*ylim)
	ax.set_aspect('equal')
	ax.set_xlabel(labels[0])
	ax.set_ylabel(labels[1])
	ax.set_title(title)
	fig.colorbar(m, ax=ax, shrink=0.8, label='|%s| peak (dB, 0 dB = %g th percentile)' % (comp, REF_PCT))
	fig.savefig(os.path.join(OUT, out))
	plt.close(fig)


def gif_phase(src, name, comp, title, overlay, xlim, ylim, out, labels, nframe=24, sym_clip=0.15):
	"""Steady-state animation of one field component at 2.44 GHz (one period)."""
	x, y, z, F = read_fd(src, name)
	u, v, F2, _ = plane2d(x, y, z, F)
	C = F2['xyz'.index(comp)]
	C = C / np.abs(C).max()
	su = (u >= xlim[0]) & (u <= xlim[1])
	sv = (v >= ylim[0]) & (v <= ylim[1])
	vmax = np.abs(C[np.ix_(su, sv)]).max() * sym_clip
	fig, ax = plt.subplots(figsize=(7, 4.6))
	m = ax.pcolormesh(u, v, np.real(C).T, shading='auto', cmap='RdBu_r', vmin=-vmax, vmax=vmax)
	overlay(ax)
	ax.set_xlim(*xlim)
	ax.set_ylim(*ylim)
	ax.set_aspect('equal')
	ax.set_xlabel(labels[0])
	ax.set_ylabel(labels[1])
	fig.colorbar(m, ax=ax, shrink=0.8, label='E%s (relative, colour clipped at %d %% of the max)' % (comp, sym_clip * 100))
	t = ax.set_title(title)

	def frame(k):
		ph = 2 * np.pi * k / nframe
		m.set_array(np.real(C * np.exp(1j * ph)).T.ravel())
		t.set_text('%s, phase %3d deg' % (title, round(np.degrees(ph))))
		return m, t
	FuncAnimation(fig, frame, frames=nframe, blit=False).save(os.path.join(OUT, out), writer=PillowWriter(fps=12))
	plt.close(fig)


def main():
	src = os.path.abspath(sys.argv[1])
	os.makedirs(OUT, exist_ok=True)
	gy = ant.base(ANT)['GND_Y']
	top_lab = ('x sim (mm) = KiCad x - 150', 'y sim (mm) = 100 - KiCad y')
	still_magnitude(src, 'fd_E_top', '|E| at 2.44 GHz, 0.05 mm above F.Cu (peak amplitude)', overlay_top,
		(-17.5, 17.5), (-17.5, 17.5), 'E_top_board.png', top_lab)
	still_magnitude(src, 'fd_E_top', '|E| at 2.44 GHz above F.Cu, antenna area', overlay_top,
		(-13, 12), (6, 17.5), 'E_top_antenna.png', top_lab)
	still_magnitude(src, 'fd_E_sub', '|E| at 2.44 GHz inside the top prepreg (between F.Cu and In1.Cu)', overlay_top,
		(-13, 12), (6, 17.5), 'E_prepreg_antenna.png', top_lab)
	still_magnitude(src, 'fd_H_top', '|H| at 2.44 GHz above F.Cu (proportional to the surface current)', overlay_top,
		(-17.5, 17.5), (-17.5, 17.5), 'H_top_board.png', top_lab)
	still_magnitude(src, 'fd_J_cu', '|J| = |rot H| at 2.44 GHz on the F.Cu plane (current on the antenna and ground)',
		overlay_top, (-17.5, 17.5), (-17.5, 17.5), 'J_FCu_board.png', top_lab, floor=-30)
	still_magnitude(src, 'fd_J_cu', '|J| at 2.44 GHz on F.Cu, antenna area', overlay_top, (-13, 12), (4, 17.5),
		'J_FCu_antenna.png', top_lab, floor=-30)
	yz_lab = ('y sim (mm)', 'z (mm), F.Cu at 1.49')
	xz_lab = ('x sim (mm)', 'z (mm), F.Cu at 1.49')
	quiver_cut(src, 'fd_E_yz_mid', 'E in the cross-section x = 0 (open arm), 2.44 GHz, arrows at phase 0',
		lambda ax: overlay_cut_yz(ax, 0.0), (4, 20), (-3, 6), 'E_cut_yz_arm.png', yz_lab, 'E')
	quiver_cut(src, 'fd_E_yz_feed', 'E in the cross-section through the feed leg (x = -5.9), 2.44 GHz',
		lambda ax: overlay_cut_yz(ax, ant.FEED_X), (4, 20), (-3, 6), 'E_cut_yz_feed.png', yz_lab, 'E')
	quiver_cut(src, 'fd_E_xz_gap', 'E in the plane y = %.1f (gap between ground edge and arm), 2.44 GHz' % ((gy + 14.6) / 2),
		lambda ax: overlay_cut_xz(ax, 12.1), (-14, 13), (-3, 6), 'E_cut_xz_gap.png', xz_lab, 'E')
	still_magnitude(src, 'fd_E_yz_mid', '|E| in the plane x = 0, whole simulated space', lambda ax: overlay_cut_yz(ax, 0.0),
		(-47, 47), (-34, 31), 'E_cut_yz_domain.png', yz_lab)
	gif_phase(src, 'fd_E_top', 'z', 'Ez above F.Cu, 2.44 GHz', overlay_top, (-13, 12), (4, 17.5), 'Ez_top_antenna.gif', top_lab,
		sym_clip=0.5)
	gif_phase(src, 'fd_E_yz_mid', 'z', 'Ez in the plane x = 0, 2.44 GHz', lambda ax: overlay_cut_yz(ax, 0.0),
		(-47, 47), (-34, 31), 'Ez_cut_yz_domain.gif', yz_lab, sym_clip=0.05)
	gif_phase(src, 'fd_E_xz_arm', 'z', 'Ez in the plane through the arm (y = 15.1), 2.44 GHz', lambda ax: overlay_cut_xz(ax, 15.1),
		(-47, 47), (-34, 31), 'Ez_cut_xz_domain.gif', xz_lab, sym_clip=0.05)
	print('wrote', OUT)


if __name__ == '__main__':
	main()

"""Render the BSN-N52 field movies and stills with ParaView (pvpython, called by make_movies.py).

BSN-N52 r7 version of the C23 render script (2026-11-15): light background, the board itself (KiCad STL export in the
sim frame: board body, copper, parts incl. the CR1632 holder and cell) under the field planes.

Usage:  pvpython render_pv.py <vtk dir from fields_to_vtk.py> <frame dir> [only,names]
Writes PNG frame sequences <frame dir>/<movie>/f<k>.png.
Field values are relative (openEMS excitation, not a set power).
"""
import os
import sys

from paraview.simple import (PVDReader, XMLRectilinearGridReader, LegacyVTKReader, STLReader, Show, Render,
	GetActiveViewOrCreate, ColorBy, GetColorTransferFunction, GetScalarBar, SaveScreenshot, GetAnimationScene,
	Calculator, Clip, GetSources, Delete)

VTK, OUT = sys.argv[1], sys.argv[2]
ONLY = sys.argv[3].split(',') if len(sys.argv) > 3 else None
HERE = os.path.dirname(os.path.abspath(__file__))
STL = os.path.join(HERE, 'geometry')
os.makedirs(OUT, exist_ok=True)
RES = [1600, 1000]
view = GetActiveViewOrCreate('RenderView')
view.ViewSize = RES
view.Background = [1, 1, 1]
try:
	view.UseColorPaletteForBackground = 0
except AttributeError:
	pass
view.OrientationAxesVisibility = 1
geo = os.path.join(VTK, 'geometry')
ZF = 1.51
ANT_C = (2.0, 6.0, 0.75)                    # about the middle of the antenna (sim frame, mm)
R_ANT = 'sqrt((coordsX-2)^2+(coordsY-6)^2+(coordsZ-0.75)^2)'
PCB = (0.55, 0.72, 0.55)
CU = (0.85, 0.58, 0.25)
PARTS = (0.62, 0.62, 0.66)


def outline(name, color=(0, 0, 0), width=2.0, opacity=1.0):
	r = LegacyVTKReader(FileNames=[os.path.join(geo, name)])
	d = Show(r, view)
	d.ColorArrayName = ['POINTS', '']
	d.AmbientColor = d.DiffuseColor = list(color)
	d.LineWidth = width
	d.Opacity = opacity
	return r, d


def solid(name, color, opacity=1.0, clip=None):
	"""Board STL from KiCad (sim frame). clip = (origin, normal): keep the side the normal points away from."""
	src = STLReader(FileNames=[os.path.join(STL, name)])
	if clip:
		c = Clip(Input=src)
		c.ClipType = 'Plane'
		c.ClipType.Origin = list(clip[0])
		c.ClipType.Normal = list(clip[1])
		c.Crinkleclip = 0
		try:
			c.Invert = 1
		except AttributeError:
			pass
		src = c
	d = Show(src, view)
	d.ColorArrayName = ['POINTS', '']
	d.AmbientColor = d.DiffuseColor = list(color)
	d.Opacity = opacity
	d.Specular = 0.2
	return d


def board(clip=None, parts=True, opacity=1.0):
	solid('board_body.stl', PCB, opacity, clip)
	solid('board_copper.stl', CU, opacity, clip)
	if parts:
		solid('board_parts.stl', PARTS, opacity, clip)


def clear():
	"""Delete every source of the previous movie (only hiding them ran the GPU out of textures on BSN)."""
	for _ in range(5):
		for s in list(GetSources().values()):
			try:
				Delete(s)
			except Exception:
				pass
	for a in ('E', 'E_mag', 'E_peak', 'Ey_r', 'Ez_r', 'H', 'H_mag', 'J', 'J_mag', 'J_peak'):
		try:
			lut = GetColorTransferFunction(a)
			lut.UseLogScale = 0
			lut.AutomaticRescaleRangeMode = 'Grow and update on \'Apply\''
			GetScalarBar(lut, view).Visibility = 0
		except Exception:
			pass


def colour(disp, array, comp=None, rng=None, cmap='Cool to Warm', log=False, title=None):
	if comp is None:
		ColorBy(disp, ('POINTS', array))
	else:
		ColorBy(disp, ('POINTS', array, comp))
	lut = GetColorTransferFunction(array)
	lut.ApplyPreset(cmap, True)
	if comp is not None:
		lut.VectorMode = 'Component'
		lut.VectorComponent = 'XYZ'.index(comp)
	lut.UseLogScale = 1 if log else 0
	if rng:
		lut.RescaleTransferFunction(*rng)
		lut.AutomaticRescaleRangeMode = 'Never'
	bar = GetScalarBar(lut, view)
	bar.Title = title or array
	bar.ComponentTitle = ''
	bar.TitleColor = bar.LabelColor = [0, 0, 0]
	bar.TitleFontSize = 18
	bar.LabelFontSize = 14
	bar.ScalarBarLength = 0.5
	bar.Visibility = 1
	disp.SetScalarBarVisibility(view, True)
	return lut


def array_range(src, array, comp=None):
	src.UpdatePipeline()
	return src.PointData[array].GetRange(-1 if comp is None else 'XYZ'.index(comp))


def camera(pos, focal, up, scale=None):
	view.CameraPosition = pos
	view.CameraFocalPoint = focal
	view.CameraViewUp = up
	if scale:
		view.CameraParallelProjection = 1
		view.CameraParallelScale = scale
	else:
		view.CameraParallelProjection = 0
		view.CameraViewAngle = 30


def frames(name, src):
	d = os.path.join(OUT, name)
	os.makedirs(d, exist_ok=True)
	scene = GetAnimationScene()
	scene.UpdateAnimationUsingDataTimeSteps()
	ts = list(src.TimestepValues) if src.TimestepValues else [0]
	if '_peak' in name:                # the peak amplitude is the same in every phase frame: one still
		ts = ts[:1]
	for k, t in enumerate(ts):
		view.ViewTime = t
		Render(view)
		SaveScreenshot(os.path.join(d, 'f%04d.png' % k), view, ImageResolution=RES)
	print(name, len(ts), 'frames', flush=True)


def wanted(name):
	return ONLY is None or name in ONLY


def movie(name, pvd, array, comp, clip, cam, title, log=False, rng=None, calc=None, cmap=None, opacity=1.0,
		under=None, extra=None):
	"""One field series on one plane over the board. under: board drawing, 'top' (whole board under a horizontal
	plane), ('clip', origin, normal) (board cut at a vertical plane, the far half shown), None (no board).
	extra: more field series shown with the same colour map (list of pvd)."""
	if not wanted(name):
		return
	clear()
	reader = src = PVDReader(FileName=os.path.join(VTK, pvd))
	if calc:
		src = Calculator(Input=reader, ResultArrayName=calc[0], Function=calc[1])
		array, comp = calc[0], None
	disp = Show(src, view)
	disp.Opacity = opacity
	signed = bool(comp or calc)
	if rng is None:
		lo, hi = array_range(src, array, comp)
		m = max(abs(lo), abs(hi)) * clip
		rng = (-m, m) if signed else ((m * 1e-3, m) if log else (0.0, m))
	colour(disp, array, comp, rng, cmap=cmap or ('Cool to Warm' if signed else 'Inferno'), log=log, title=title)
	for p in extra or []:
		e = Show(PVDReader(FileName=os.path.join(VTK, p)), view)
		e.Opacity = opacity
		ColorBy(e, ('POINTS', array, comp) if comp else ('POINTS', array))
	if under == 'top':
		board(parts=False)
		outline('antenna_AE1_outline.vtk', (0, 0, 0), 2.0)
		outline('board_outline_top.vtk', (0.1, 0.1, 0.1), 2.0)
	elif under == '3d':
		board()
	elif isinstance(under, tuple):
		# cut 0.05 mm on the camera side of the field plane, so the cut face of the board shows over the field
		o = [c + 0.05 * n for c, n in zip(under[1], under[2])]
		board(clip=(o, under[2]))
	Render(view)                        # the first render resets the camera, set ours after it
	camera(*cam)
	frames(name, reader)


def td_peak(pvd, array):
	src = PVDReader(FileName=os.path.join(VTK, pvd))
	m = 0
	for t in src.TimestepValues:
		src.UpdatePipeline(t)
		m = max(m, src.PointData[array].GetRange(-1)[1])
	Delete(src)
	return m


def wave_range(pvd, comp, rmin, pct=99.0, frames=(0, 9)):
	"""Percentile of |E_comp| * r over the far part of the plane (numpy on the phase vtr files)."""
	import numpy as np
	from vtkmodules.vtkIOXML import vtkXMLRectilinearGridReader
	from vtkmodules.util.numpy_support import vtk_to_numpy
	vals = []
	for k in frames:
		r = vtkXMLRectilinearGridReader()
		r.SetFileName(os.path.join(VTK, pvd.replace('.pvd', ''), 'p%02d.vtr' % k))
		r.Update()
		g = r.GetOutput()
		x, y, z = (vtk_to_numpy(c()) for c in (g.GetXCoordinates, g.GetYCoordinates, g.GetZCoordinates))
		Z, Y, X = np.meshgrid(z, y, x, indexing='ij')
		d = np.sqrt((X - ANT_C[0]) ** 2 + (Y - ANT_C[1]) ** 2 + (Z - ANT_C[2]) ** 2).ravel()
		e = vtk_to_numpy(g.GetPointData().GetArray('E'))[:, 'XYZ'.index(comp)]
		vals.append(np.abs(e * d)[d > rmin])
	return float(np.percentile(np.concatenate(vals), pct))


def half_size(pvd):
	r = XMLRectilinearGridReader(FileName=[os.path.join(VTK, pvd.replace('.pvd', ''), 'p00.vtr')])
	r.UpdatePipeline()
	b = r.GetDataInformation().GetBounds()
	Delete(r)
	return max(b[1] - b[0], b[3] - b[2], b[5] - b[4]) / 2


# cameras (pos, focal, up, parallel scale or None = perspective). Sim frame: antenna along the top edge (y 3.6..8.2),
# cell under the board around (0, -4.5), F.Cu up (+z).
TOP = ([0, 0, 200], [0, 0, 1.5], [0, 1, 0], 13.5)
TOP_WIDE = ([0, 0, 200], [0, 0, 1.5], [0, 1, 0], 24)
BOTTOM = ([0, 0, -200], [0, 0, 0], [0, 1, 0], 13.5)
SIDE_YZ = ([200, 0, 0], [0, 0, 0], [0, 0, 1], 14)
SIDE_FEED = ([200, 0, 0], [-4, 2, 0], [0, 0, 1], 9)
FRONT_XZ = ([0, -200, 0], [0, 0, 0], [0, 0, 1], 18)
ISO = ([-38, -55, 42], [1, 0, -0.5], [0, 0, 1], None)


def main():
	# 2.44 GHz steady state, one period (phase movies)
	movie('Ez_top_phase', 'fd/fd_E_top.pvd', 'E', 'Z', 0.35, TOP, 'Ez 0.05 mm above F.Cu, 2.44 GHz (relative)',
		opacity=0.82, under='top')
	movie('E_top_peak_wide', 'fd/fd_E_top.pvd', 'E_peak', None, 1.0, TOP_WIDE, '|E| peak above F.Cu, 2.44 GHz (log, relative)',
		log=True, opacity=0.85, under='top')
	movie('J_top_phase', 'fd/fd_J_F.pvd', 'J_mag', None, 0.5, TOP, 'surface current F.Cu, 2.44 GHz (relative)',
		cmap='Inferno', opacity=0.9, under='top')
	movie('J_bottom_phase', 'fd/fd_J_B.pvd', 'J_mag', None, 0.5, BOTTOM, 'surface current B.Cu, 2.44 GHz (relative)',
		cmap='Inferno', opacity=0.9, under=None)
	movie('Ez_yz_mid_phase', 'fd/fd_E_yz_mid.pvd', 'E', 'Z', 0.08, SIDE_YZ,
		'Ez in the plane x = 0 (board and cell cut), 2.44 GHz (relative)', under=('clip', [0, 0, 0], [1, 0, 0]))
	movie('E_yz_feed_phase', 'fd/fd_E_yz_feed.pvd', 'E_mag', None, 0.3, SIDE_FEED,
		'|E| in the plane through the feed, 2.44 GHz (relative)', cmap='Inferno', under=('clip', [-4, 0, 0], [1, 0, 0]))
	movie('Ez_xz_arm_phase', 'fd/fd_E_xz_arm.pvd', 'E', 'Z', 0.08, FRONT_XZ,
		'Ez in the plane through the antenna arm, 2.44 GHz (relative)', under=('clip', [0, 7.65, 0], [0, -1, 0]))
	movie('E_bot_peak', 'fd/fd_E_bot.pvd', 'E_peak', None, 1.0, BOTTOM,
		'|E| peak between B.Cu and the cell, 2.44 GHz (log, relative)', log=True, opacity=0.85, under=None)
	movie('Ez_3d_phase', 'fd/fd_E_yz_mid.pvd', 'E', 'Z', 0.08, ISO, 'Ez, planes x = 0 and through the arm, 2.44 GHz (relative)',
		under='3d', extra=['fd/fd_E_xz_arm.pvd'], opacity=0.9)

	# radiated wave: component x distance (the 1/r fall-off hides the wavefronts otherwise), only on big planes
	h = half_size('fd/fd_E_yz_mid.pvd')
	if h > 60:
		rmin = 0.5 * h
		wide = 0.95 * h
		for name, pvd, comp, cam, cl, where in (
				('Ez_r_yz_wave', 'fd/fd_E_yz_mid.pvd', 'Z', ([600, 0, 0], [0, 0, 0], [0, 0, 1], wide), ([0, 0, 0], [1, 0, 0]), 'plane x = 0'),
				('Ez_r_xz_wave', 'fd/fd_E_xz_arm.pvd', 'Z', ([0, -600, 0], [0, 0, 0], [0, 0, 1], wide), ([0, 7.65, 0], [0, -1, 0]), 'plane through the arm'),
				('Ey_r_xz_wave', 'fd/fd_E_xz_arm.pvd', 'Y', ([0, -600, 0], [0, 0, 0], [0, 0, 1], wide), ([0, 7.65, 0], [0, -1, 0]), 'plane through the arm')):
			if not wanted(name):
				continue
			m = wave_range(pvd, comp, rmin)
			movie(name, pvd, None, None, 1, cam, 'E%s x distance, %s, 2.44 GHz (relative, shows the wavefronts)' % (comp.lower(), where),
				rng=(-m, m), calc=('E%s_r' % comp.lower(), 'E_%s*%s' % (comp, R_ANT)), under=('clip', cl[0], cl[1]))

	# Gaussian pulse in time (log |E|), one colour range for the whole pulse
	for name, pvd, cam, under in (('td_E_top', 'td/td_E_top.pvd', TOP_WIDE, 'top'),
			('td_E_yz_mid', 'td/td_E_yz_mid.pvd', ([600, 0, 0], [0, 0, 0], [0, 0, 1], 0.95 * h), ('clip', [0, 0, 0], [1, 0, 0])),
			('td_E_xz_arm', 'td/td_E_xz_arm.pvd', ([0, -600, 0], [0, 0, 0], [0, 0, 1], 0.95 * h), ('clip', [0, 7.65, 0], [0, -1, 0])),
			('td_E_yz_near', 'td/td_E_yz_mid.pvd', SIDE_YZ, ('clip', [0, 0, 0], [1, 0, 0]))):
		if not wanted(name) or not os.path.exists(os.path.join(VTK, pvd)):
			continue
		m = td_peak(pvd, 'E_mag')
		movie(name, pvd, 'E_mag', None, 1, cam, '|E| of the pulse 1.25-3.65 GHz (log, relative)', log=True,
			rng=(m * 1e-3, m * 0.3), under=under, opacity=0.85 if under == 'top' else 1.0)


if __name__ == '__main__':
	main()

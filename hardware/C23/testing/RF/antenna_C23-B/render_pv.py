"""Render field movies and stills with ParaView (run with pvpython, called by make_movies.py).

Usage:  pvpython render_pv.py <vtk dir from fields_to_vtk.py> <frame dir>
Writes PNG frame sequences <frame dir>/<movie>/f<k>.png and stills <frame dir>/<name>.png.
"""
import os
import sys

from paraview.simple import (PVDReader, XMLRectilinearGridReader, LegacyVTKReader, Show, Hide, Render,
	GetActiveViewOrCreate, ColorBy, GetColorTransferFunction, GetOpacityTransferFunction, GetScalarBar,
	SaveScreenshot, GetAnimationScene, UpdatePipeline, Calculator, GetSources, Delete)

VTK, OUT = sys.argv[1], sys.argv[2]
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


def outline(name, color=(0, 0, 0), width=2.0, opacity=1.0):
	r = LegacyVTKReader(FileNames=[os.path.join(geo, name)])
	d = Show(r, view)
	d.ColorArrayName = ['POINTS', '']
	d.AmbientColor = d.DiffuseColor = list(color)
	d.LineWidth = width
	d.Opacity = opacity
	return r, d


def clear():
	"""Delete every source of the previous movie. Only hiding them kept all readers and colour maps alive and the
	last movies rendered solid magenta ("Hardware does not support the number of textures defined")."""
	for _ in range(4):                 # filters before their inputs, a few passes
		for s in list(GetSources().values()):
			try:
				Delete(s)
			except Exception:
				pass
	for a in ('E', 'E_mag', 'E_peak', 'Ey_r', 'H', 'H_mag'):
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
	if log:
		lut.UseLogScale = 1
	if rng:
		lut.RescaleTransferFunction(*rng)
		lut.AutomaticRescaleRangeMode = 'Never'
	bar = GetScalarBar(lut, view)
	bar.Title = title or array
	bar.ComponentTitle = ''
	bar.TitleColor = bar.LabelColor = [0, 0, 0]
	bar.Visibility = 1
	disp.SetScalarBarVisibility(view, True)
	return lut


def array_range(src, array, comp=None):
	src.UpdatePipeline()
	a = src.PointData[array]
	return a.GetRange(-1 if comp is None else 'XYZ'.index(comp))


def camera(pos, focal, up, scale=None):
	c = view.GetActiveCamera()
	view.CameraPosition = pos
	view.CameraFocalPoint = focal
	view.CameraViewUp = up
	if scale:
		view.CameraParallelProjection = 1
		view.CameraParallelScale = scale
	else:
		view.CameraParallelProjection = 0


def frames(name, src):
	"""Save one PNG per time step of the animation scene."""
	d = os.path.join(OUT, name)
	os.makedirs(d, exist_ok=True)
	scene = GetAnimationScene()
	scene.UpdateAnimationUsingDataTimeSteps()
	ts = list(src.TimestepValues) if src.TimestepValues else [0]
	for k, t in enumerate(ts):
		view.ViewTime = t
		Render(view)
		SaveScreenshot(os.path.join(d, 'f%04d.png' % k), view, ImageResolution=RES)
	print(name, len(ts), 'frames', flush=True)


def movie_plane(name, pvd, array, comp, clip, cam, title, log=False, rng=None, calc=None):
	"""calc: (result name, ParaView Calculator expression), the movie is coloured by that instead of array."""
	clear()
	reader = src = PVDReader(FileName=os.path.join(VTK, pvd))
	if calc:
		src = Calculator(Input=reader, ResultArrayName=calc[0], Function=calc[1])
		array, comp = calc[0], None
	disp = Show(src, view)
	if rng is None:
		lo, hi = array_range(src, array, comp)
		m = max(abs(lo), abs(hi)) * clip
		rng = (-m, m) if (comp or calc) else ((m * 1e-3, m) if log else (0.0, m))
	colour(disp, array, comp, rng, cmap='Cool to Warm' if (comp or calc) else 'Inferno', log=log, title=title)
	outline('antenna_AE1_outline.vtk', (0, 0, 0), 2.5)
	outline('board_outline_top.vtk', (0.2, 0.2, 0.2), 1.5)
	outline('copper_FCu.vtk', (0.35, 0.35, 0.35), 0.8, 0.6)
	Render(view)                       # the first render resets the camera, set ours after it
	camera(*cam)
	frames(name, reader)
	return src


def td_peak(pvd, array):
	"""Largest value over all time samples (sets one colour range for the whole pulse movie)."""
	src = PVDReader(FileName=os.path.join(VTK, pvd))
	m = 0
	for t in src.TimestepValues:
		src.UpdatePipeline(t)
		m = max(m, src.PointData[array].GetRange(-1)[1])
	return src, m


TOP = ([0, 0, 200], [0, 3, 1.5], [0, 1, 0], 20)
TOP_ANT = ([-1, 11, 200], [-1, 11, 1.5], [0, 1, 0], 9)
SIDE_YZ = ([300, 0, 0], [0, 0, 0], [0, 0, 1], 34)
SIDE_YZ_NEAR = ([300, 12, 1.5], [0, 12, 1.5], [0, 0, 1], 9)
FRONT_XZ = ([0, -300, 0], [0, 0, 0], [0, 0, 1], 34)
# whole dumped plane of a run with mesh air 150 (planes about +-169 x +-155 mm)
WIDE_YZ = ([600, 0, 0], [0, 0, 0], [0, 0, 1], 160)
WIDE_XZ = ([0, -600, 0], [0, 0, 0], [0, 0, 1], 160)
# Ey times the distance from the antenna (about x 0, y 12, z 1.5): the radiated field falls as 1/r, so the
# wavefronts keep their contrast out to the edge of the domain. Only for showing the wave, not a field value.
# Ey carries most of the radiated field in both side planes of the b3 run (far region 2x Ex, 8x Ez), and it is
# fully transverse in the xz plane. The colour range is the 99th percentile at r > 60 mm, the near field is
# 10-70x stronger and saturates on purpose.
ANT_C = (0.0, 12.0, 1.5)
R_ANT = 'sqrt(coordsX^2+(coordsY-12)^2+(coordsZ-1.5)^2)'
EY_R = ('Ey_r', 'E_Y*' + R_ANT)


def wave_range(pvd, comp='Y', rmin=60.0, pct=99.0, frames=(0, 9)):
	"""Percentile of |E_comp| * r over the far part of the plane, for a few phase frames (numpy on the vtr files)."""
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
		Z, Y, X = np.meshgrid(z, y, x, indexing='ij')           # VTK order, x fastest
		d = np.sqrt((X - ANT_C[0]) ** 2 + (Y - ANT_C[1]) ** 2 + (Z - ANT_C[2]) ** 2).ravel()
		e = vtk_to_numpy(g.GetPointData().GetArray('E'))[:, 'XYZ'.index(comp)]
		vals.append(np.abs(e * d)[d > rmin])
	return float(np.percentile(np.concatenate(vals), pct))


def wide(pvd):
	"""True when the plane is the big one of a mesh-air-150 run."""
	r = XMLRectilinearGridReader(FileName=[os.path.join(VTK, pvd.replace('.pvd', ''), 'p00.vtr')])
	r.UpdatePipeline()
	b = r.GetDataInformation().GetBounds()
	return max(b[1] - b[0], b[3] - b[2], b[5] - b[4]) > 150

if __name__ == '__main__':
	movie_plane('Ez_top_phase', 'fd/fd_E_top.pvd', 'E', 'Z', 0.4, TOP_ANT, 'Ez above F.Cu, 2.44 GHz (relative)')
	movie_plane('Ez_yz_phase', 'fd/fd_E_yz_mid.pvd', 'E', 'Z', 0.05, SIDE_YZ, 'Ez in the plane x = 0, 2.44 GHz (relative)')
	movie_plane('Ez_xz_phase', 'fd/fd_E_xz_arm.pvd', 'E', 'Z', 0.05, FRONT_XZ, 'Ez in the plane through the arm, 2.44 GHz (relative)')
	movie_plane('E_yz_near_phase', 'fd/fd_E_yz_mid.pvd', 'E_mag', None, 0.3, SIDE_YZ_NEAR, '|E| between arm and ground, x = 0 (relative)')
	big = wide('fd/fd_E_yz_mid.pvd')
	if big:
		for name, pvd, cam, where in (('Ey_r_yz_wave', 'fd/fd_E_yz_mid.pvd', WIDE_YZ, 'plane x = 0'),
				('Ey_r_xz_wave', 'fd/fd_E_xz_arm.pvd', WIDE_XZ, 'plane through the arm')):
			m = wave_range(pvd)
			movie_plane(name, pvd, None, None, 1, cam, 'Ey x distance, %s, 2.44 GHz (relative, shows the wavefronts)' % where,
				rng=(-m, m), calc=EY_R)
	td = [('td_E_top', 'td/td_E_top.pvd', TOP), ('td_E_yz', 'td/td_E_yz_mid.pvd', SIDE_YZ),
		('td_E_xz', 'td/td_E_xz_arm.pvd', FRONT_XZ)]
	if big:
		td += [('td_E_yz_wide', 'td/td_E_yz_mid.pvd', WIDE_YZ), ('td_E_xz_wide', 'td/td_E_xz_arm.pvd', WIDE_XZ)]
	for name, pvd, cam in td:
		if not os.path.exists(os.path.join(VTK, pvd)):
			continue
		_, m = td_peak(pvd, 'E_mag')
		movie_plane(name, pvd, 'E_mag', None, 1, cam, '|E| (Gaussian pulse 1.45-3.45 GHz, log scale)', log=True,
			rng=(m * 1e-3, m * 0.3))

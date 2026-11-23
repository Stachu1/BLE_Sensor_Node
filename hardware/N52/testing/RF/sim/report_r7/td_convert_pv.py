"""Run with ParaView's pvpython (called by fields_to_vtk.py). Rewrites the openEMS time-domain .vtr samples
in mm (openEMS writes metres) with the arrays E or H and their magnitude, and writes one .pvd per series.

Usage:  pvpython td_convert_pv.py <sim_e0 dir> <out td dir> <dt in s>
"""
import glob
import os
import re
import sys

import numpy as np
from vtkmodules.vtkIOXML import vtkXMLRectilinearGridReader, vtkXMLRectilinearGridWriter
from vtkmodules.util.numpy_support import vtk_to_numpy, numpy_to_vtk

src, out, dt = sys.argv[1], sys.argv[2], float(sys.argv[3])
os.makedirs(out, exist_ok=True)
series = {}
for p in glob.glob(os.path.join(src, 'td_*.vtr')):
	m = re.match(r'(td_.+)_(\d+)\.vtr$', os.path.basename(p))
	if m:
		series.setdefault(m.group(1), []).append((int(m.group(2)), p))
for name, lst in sorted(series.items()):
	lst.sort()
	qty = name.split('_')[1]
	d = os.path.join(out, name)
	os.makedirs(d, exist_ok=True)
	items = []
	for k, (n, p) in enumerate(lst):
		r = vtkXMLRectilinearGridReader()
		r.SetFileName(p)
		r.Update()
		g = r.GetOutput()
		for get, setc in ((g.GetXCoordinates, g.SetXCoordinates), (g.GetYCoordinates, g.SetYCoordinates),
				(g.GetZCoordinates, g.SetZCoordinates)):
			setc(numpy_to_vtk(vtk_to_numpy(get()).astype(np.float64) * 1e3, deep=1))
		pd = g.GetPointData()
		a = pd.GetArray(0)
		v = vtk_to_numpy(a).astype(np.float32)
		pd.RemoveArray(a.GetName())
		va = numpy_to_vtk(v, deep=1)
		va.SetName(qty)
		pd.AddArray(va)
		ma = numpy_to_vtk(np.sqrt((v.astype(np.float64) ** 2).sum(axis=1)).astype(np.float32), deep=1)
		ma.SetName('%s_mag' % qty)
		pd.AddArray(ma)
		w = vtkXMLRectilinearGridWriter()
		w.SetFileName(os.path.join(d, 't%04d.vtr' % k))
		w.SetInputData(g)
		w.SetDataModeToBinary()
		w.SetCompressorTypeToZLib()
		w.Write()
		items.append((n * dt * 1e9, '%s/t%04d.vtr' % (name, k)))
	with open(os.path.join(out, name + '.pvd'), 'w') as fh:
		fh.write('<?xml version="1.0"?>\n<VTKFile type="Collection" version="0.1">\n<Collection>\n')
		for t, f in items:
			fh.write('<DataSet timestep="%.6g" file="%s"/>\n' % (t, f))
		fh.write('</Collection>\n</VTKFile>\n')
	print('%-14s %d samples, 0 .. %.2f ns' % (name, len(lst), lst[-1][0] * dt * 1e9), flush=True)

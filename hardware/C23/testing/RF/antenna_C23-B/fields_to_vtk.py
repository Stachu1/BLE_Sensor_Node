"""Convert the openEMS field dumps of the detailed run into ParaView files.

Input: the run's sim_e0 folder (copied from the server, see README), with
    fd_<E|H>_<plane>.h5, fd_J_cu.h5, fd_<E|H>_vol.h5   2.44 GHz phasors (hdf5)
    td_<E|H>_<plane>_<step>.vtr                         time-domain samples written by openEMS
Output in <out>:
    fd/<name>.pvd + fd/<name>/p<k>.vtr  phase animation of the 2.44 GHz steady state: field(t) = Re(F e^(j wt)),
                                        one period in NPHASE frames. Arrays: vector field, its magnitude and
                                        the peak amplitude |F| (same in every frame, good for a still picture).
    td/<name>.pvd                       the openEMS time samples as one series with the time in ns
Coordinates are written in mm in the simulation frame (x_sim = x_kicad - 150, y_sim = 100 - y_kicad, z up from
B.Cu, F.Cu at z 1.486 mm).

Usage:  python fields_to_vtk.py <sim_e0 dir> <out dir> [nphase]
"""
import glob
import os
import re
import sys

import h5py
import numpy as np

NPHASE = 36
DT = 1.77722e-13       # overwritten from run.log when it is found next to sim_e0


def write_vtr(path, x, y, z, arrays):
	"""VTK XML RectilinearGrid, raw appended float32 data. arrays: {name: (n,) or (n, 3)} in x-fastest order."""
	blocks = [np.asarray(x, '<f4'), np.asarray(y, '<f4'), np.asarray(z, '<f4')]
	names = []
	for n, a in arrays.items():
		a = np.asarray(a, '<f4')
		blocks.append(a)
		names.append((n, 1 if a.ndim == 1 else a.shape[1]))
	offs, o = [], 0
	for b in blocks:
		offs.append(o)
		o += 4 + b.nbytes
	ext = '0 %d 0 %d 0 %d' % (len(x) - 1, len(y) - 1, len(z) - 1)
	h = ['<?xml version="1.0"?>',
		'<VTKFile type="RectilinearGrid" version="0.1" byte_order="LittleEndian" header_type="UInt32">',
		'<RectilinearGrid WholeExtent="%s"><Piece Extent="%s">' % (ext, ext), '<PointData>']
	for (n, nc), off in zip(names, offs[3:]):
		h.append('<DataArray type="Float32" Name="%s" NumberOfComponents="%d" format="appended" offset="%d"/>' % (n, nc, off))
	h.append('</PointData><Coordinates>')
	for k, c in enumerate('xyz'):
		h.append('<DataArray type="Float32" Name="%s" format="appended" offset="%d"/>' % (c, offs[k]))
	h += ['</Coordinates></Piece></RectilinearGrid>', '<AppendedData encoding="raw">']
	with open(path, 'wb') as fh:
		fh.write(('\n'.join(h) + '\n_').encode())
		for b in blocks:
			fh.write(np.uint32(b.nbytes).tobytes())
			fh.write(b.tobytes())
		fh.write(b'\n</AppendedData></VTKFile>\n')


def write_pvd(path, items):
	with open(path, 'w') as fh:
		fh.write('<?xml version="1.0"?>\n<VTKFile type="Collection" version="0.1">\n<Collection>\n')
		for t, f in items:
			fh.write('<DataSet timestep="%.6g" file="%s"/>\n' % (t, f))
		fh.write('</Collection>\n</VTKFile>\n')


def read_fd(path):
	h = h5py.File(path, 'r')
	x, y, z = (np.array(h['Mesh'][k], float) * 1e3 for k in 'xyz')     # m -> mm
	F = np.array(h['FieldData/FD/f0']).astype(complex)                   # (3, nx, ny, nz)
	assert F.shape[1:] == (len(x), len(y), len(z)), (F.shape, len(x), len(y), len(z))
	return x, y, z, F


def convert_fd(src, out, nphase):
	os.makedirs(os.path.join(out, 'fd'), exist_ok=True)
	for p in sorted(glob.glob(os.path.join(src, 'fd_*.h5'))):
		name = os.path.splitext(os.path.basename(p))[0]
		qty = name.split('_')[1]                                         # E, H or J
		x, y, z, F = read_fd(p)
		V = F.transpose(3, 2, 1, 0).reshape(-1, 3)                       # x fastest
		amp = np.sqrt(np.sum(np.abs(V) ** 2, axis=1))
		d = os.path.join(out, 'fd', name)
		os.makedirs(d, exist_ok=True)
		items = []
		for k in range(nphase):
			ph = 2 * np.pi * k / nphase
			R = np.real(V * np.exp(1j * ph))
			write_vtr(os.path.join(d, 'p%02d.vtr' % k), x, y, z,
				{qty: R, '|%s|' % qty: np.sqrt(np.sum(R ** 2, axis=1)), '%s peak' % qty: amp})
			items.append((k / nphase, '%s/p%02d.vtr' % (name, k)))
		write_pvd(os.path.join(out, 'fd', name + '.pvd'), items)
		print('%-14s %s points, %d phases' % (name, 'x'.join(map(str, (len(x), len(y), len(z)))), nphase), flush=True)


def convert_td(src, out, dt):
	os.makedirs(os.path.join(out, 'td'), exist_ok=True)
	series = {}
	for p in glob.glob(os.path.join(src, 'td_*.vtr')):
		m = re.match(r'(td_.+)_(\d+)\.vtr$', os.path.basename(p))
		if m:
			series.setdefault(m.group(1), []).append((int(m.group(2)), p))
	for name, lst in sorted(series.items()):
		lst.sort()
		rel = os.path.relpath(src, os.path.join(out, 'td')).replace('\\', '/')
		write_pvd(os.path.join(out, 'td', name + '.pvd'),
			[(n * dt * 1e9, '%s/%s' % (rel, os.path.basename(p))) for n, p in lst])
		print('%-14s %d samples, %.2f ns' % (name, len(lst), lst[-1][0] * dt * 1e9), flush=True)


def main():
	src, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
	nphase = int(sys.argv[3]) if len(sys.argv) > 3 else NPHASE
	dt = DT
	log = os.path.join(os.path.dirname(src), 'run.log')
	if os.path.exists(log):
		m = re.search(r'FDTD timestep is: ([0-9.eE+-]+) s', open(log).read())
		if m:
			dt = float(m.group(1))
	convert_fd(src, out, nphase)
	convert_td(src, out, dt)


if __name__ == '__main__':
	main()

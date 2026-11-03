"""Reference check of the NF2FF efficiency evaluation used in sim_board.py: a lossless half-wave strip dipole
in free space must give a radiation efficiency close to 100 % and a directivity close to 2.15 dBi.

Usage (server): python check_efficiency.py <out_dir> [threads]
"""
import os
import sys

import numpy as np
from CSXCAD import ContinuousStructure
from openEMS import openEMS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim_board import graded_lines, NF2FF_F, F, NF2FF_OS  # noqa: E402
from farfield import farfield  # noqa: E402

out = os.path.abspath(sys.argv[1])
threads = int(sys.argv[2]) if len(sys.argv) > 2 else 4
os.makedirs(out, exist_ok=True)
L, W, gap = 57.0, 1.0, 1.0

FDTD = openEMS(NrTS=400000, EndCriteria=1e-4)
FDTD.SetGaussExcite(2.45e9, 0.75e9)
FDTD.SetBoundaryCond(['PML_8'] * 6)
CSX = ContinuousStructure()
FDTD.SetCSX(CSX)
grid = CSX.GetGrid()
grid.SetDeltaUnit(1e-3)
cu = CSX.AddMetal('Cu')
cu.AddBox([-W / 2, gap / 2, 0], [W / 2, L / 2, 0], priority=10)
cu.AddBox([-W / 2, -L / 2, 0], [W / 2, -gap / 2, 0], priority=10)
port = FDTD.AddLumpedPort(1, 73, [-W / 2, -gap / 2, 0], [W / 2, gap / 2, 0], 'y', excite=1.0, priority=20)
air = 32
grid.AddLine('x', graded_lines([-W / 2, W / 2], [(-1, 1, 0.25)], -air, air, 4, 1.3, 0.05))
grid.AddLine('y', graded_lines([-L / 2, -gap / 2, gap / 2, L / 2], [(-L / 2 - 1, L / 2 + 1, 0.5)], -L / 2 - air, L / 2 + air, 4, 1.3, 0.05))
grid.AddLine('z', graded_lines([0], [(-1, 1, 0.25)], -air, air, 4, 1.3, 0.05))
nf = FDTD.CreateNF2FFBox('nf2ff', [-20, -L / 2 - 10, -20], [20, L / 2 + 10, 20], frequency=NF2FF_F, over_sampling=NF2FF_OS)
FDTD.Run(os.path.join(out, 'sim'), verbose=0, numThreads=threads, cleanup=True)
port.CalcPort(os.path.join(out, 'sim'), F)
u, i = port.uf_tot, port.if_tot
res = nf.CalcNF2FF(os.path.join(out, 'sim'), NF2FF_F, np.arange(0, 181, 5), np.arange(0, 361, 5), read_cached=False)
for k, f in enumerate(NF2FF_F):
	j = int(np.argmin(np.abs(F - f)))
	pacc = 0.5 * np.real(u[j] * np.conj(i[j]))
	ff = farfield(os.path.join(out, 'sim'), f, np.arange(0, 181, 5), np.arange(0, 361, 5), fidx=k)
	print('f %.2f GHz  Zin %.1f%+.1fj  openEMS: rad_eff %.3f Dmax %.2f dBi | own: rad_eff %.3f Dmax %.2f dBi flux %.3f' % (
		f / 1e9, (u[j] / i[j]).real, (u[j] / i[j]).imag, res.Prad[k] / pacc, 10 * np.log10(res.Dmax[k]),
		ff['Prad'] / pacc, ff['Dmax_dBi'], ff['flux'] / pacc), flush=True)

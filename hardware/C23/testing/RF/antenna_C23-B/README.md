# C23 rev B antenna: chosen design

Work in progress (2026-11-04). This folder collects the results of the chosen rev B antenna for the report: IFA
H5.0 L9.0 (footprint `IFA_2G4`) with L2 1.6 nH (Murata LQG15WZ1N6B02D) and L3 6.8 nH (Murata LQW15AN6N8G80D).
The design search and the reasons for the choice are in [`../sim/results/RECOMMENDATION.md`](../sim/results/RECOMMENDATION.md).

The figures and data here so far come from the b2 board runs `5393b94279` (1-port, mask, fine mesh) and
`5b8536e8e4` (3-port J2 / L2 / L3, mask, fine mesh). They will be redone on the board with rounded tracks, together
with a detailed run that has L2 and L3 as lumped parts in the FDTD model and keeps the field data for ParaView.

| file | does |
|---|---|
| `make_figures.py` | S11, Smith chart, impedance, VSWR, pattern, efficiency budget, tolerance, antenna drawing -> `figures/`, `data/` |
| `field_pictures.py` | still pictures and GIFs of the fields from the kept field dumps |
| `fields_to_vtk.py` | field dumps -> ParaView files (2.44 GHz phase animation and the time-domain pulse) |
| `td_convert_pv.py` | helper run with ParaView's pvpython, converts the openEMS time-domain files to mm |

The case lists for the new runs are `../sim/cases/fields_smoke.json`, `fields_final.json` and `fields_wave.json`.
`sim_board.py` got two case keys for them: `parts` (real L2 / L3 as series R-L lumped elements) and `field_dumps`.

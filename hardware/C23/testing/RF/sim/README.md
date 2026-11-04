# C23 rev B antenna simulations (openEMS)

Scripted pipeline from `hardware/C23/BSN-C23.kicad_pcb` to openEMS on the compute server. Nothing is
exported or meshed by hand, so every result belongs to a known board file and a known antenna.

**Results:** [`results/DESIGNS.md`](results/DESIGNS.md) ranks every simulated design. Each design has a record
in `results/designs/<run>/summary.md` with the reason for the run, the antenna dimensions in KiCad
coordinates, a drawing, the impedance at J2, the best matching parts, efficiency and the radiation pattern.

## Model

- **Board:** all four copper layers from the KiCad file (zones refilled in memory, tracks, pads), the board
  outline with the R10 corners and the JLC 7628 stack-up from the board file. Copper is modelled as
  zero-thickness metal sheets. The antenna AE1 is left out of the export and drawn by `antenna.py`, so a new
  antenna does not need a new export.
- **Vias:** a solid metal barrel the size of the drilled hole where the mesh resolves it (antenna area, ground
  edge, RF path), a single wire elsewhere.
- **Port:** J2 pad 1, the antenna side of the MM8130 switch, against the J2 ground pads on both sides. That
  is where the VNA probe measures, so simulated and measured S11 share the same reference plane. L2 is
  fitted as 0R and L3 is open.
- **Pi network:** left out. With the probe inserted the MM8130 switch disconnects C7, the pi network and U1
  from the antenna path. Their pads and traces are still in the model as copper.
- **4-port mode:** ports at J2, across the L2 gap and at the shunt pads. The Touchstone file lets `match.py`
  try matching parts without a new EM run.
- **Battery:** CR2032 as a 20 mm metal disc 0.5 mm under B.Cu, with simplified holder clips to the BT1 pads.
- **Solder mask:** not in the search runs (a 20 µm layer needs a much smaller timestep). An explicit mask run
  of the first AE1 moved the resonance down by 25 MHz (1 %), applied as a target offset.
- **Efficiency and pattern:** from our own near-to-far-field transform (`farfield.py`) of the field on a box
  around the board at 2.40, 2.44 and 2.48 GHz. The openEMS NF2FF transform gives wrong results for this
  layered board (30 % instead of 100 % on a lossless test case, box-size dependent), see `farfield.py`.
  Radiation efficiency = radiated / accepted power, total efficiency = radiated / incident power (50 ohm).
- **Real matching parts:** case key `parts` puts L2 and L3 into the FDTD model as series R-L lumped elements on
  their pads (R = wL/Q at 2.44 GHz), with the port at J2. The b3 report runs compare it with the 3-port cascade.
- **Field dumps:** case key `field_dumps` keeps E and H on planes (above F.Cu, in the top prepreg, cuts through
  the arm, the feed and the gap) and in a volume around the board, at 2.44 GHz and in the time domain, for
  pictures and movies. See `../antenna_C23-B/`.
- **Board revisions:** `build/board.json` is the first rev B layout (b1). `build/b2/` is the layout with the
  antenna-side L4 removed (after re-annotation the ref L4 is the 10 uH DC-DC inductor) and the ground edge 1.4 mm lower. `stretch_board.py` makes taller or wider copies (`build/b2t*`,
  `build/b2w*`) to see what a bigger board would gain. `build/b3/` is the board as ordered (rounded tracks, final
  AE1 footprint, via fence at KiCad y 90.7), simulated with `"antenna": "placed"` (AE1 copper from the board). `antenna.BASES` holds the ground edge of each.

## Files

| file | runs on | does |
|---|---|---|
| `export_board.py` | laptop, KiCad python | `BSN-C23.kicad_pcb` -> `build/<rev>/board.json` |
| `stretch_board.py` | laptop | taller or wider copy of an exported board |
| `antenna.py` | both | antenna families (`ifa`, `fifa` bent or folded IFA), geometry rules (edge, corners, notch) |
| `sim_board.py` | server | builds and runs one case (`case.json`), writes `result.json`, `S11.csv`, `S4P.s4p`, `pattern.npz` |
| `sim_ports.py` | both | port positions from the exported pads |
| `farfield.py` | both | near-to-far-field transform from the openEMS box dumps |
| `runner.py` | server | runs a list of cases in parallel, caches results by case content |
| `queue.sh` | server | job queue that keeps the server busy (starts jobs within a thread budget) |
| `tune2d.py`, `optimize.py` | server | tuners (Newton on Z at one frequency, compass search) |
| `match_ideal.py` | laptop | worst BLE S11 with the best ideal 1- and 2-part match at J2 |
| `match.py` | laptop | real L2/L3 parts from a 4-port result |
| `draw_antennas.py` | laptop | drawing of every antenna in a case list, KiCad coordinates and edge clearance |
| `archive.py` | laptop | design records `results/designs/` and `results/DESIGNS.md` |
| `report.py` | laptop | `results/REPORT.md` and plots |
| `check_efficiency.py` | server | reference check: half-wave dipole in free space (100 %, 2.15 dBi) |
| `simple_ifa.py`, `poynting_check.py` | both | test bench for the method (plain IFA, optional 4-layer stack and battery) |
| `sim.sh` | laptop | `export`, `push`, `run`, `queue`, `qstatus`, `opt`, `status`, `pull` |

## Use

```bash
./sim.sh export                              # after any board change (or export_board.py into build/<rev>)
python draw_antennas.py cases/my_cases.json  # check the geometry first
./sim.sh queue cases/my_cases.json 6 3       # list of {"name", "purpose", "case"}, 6 parallel x 3 threads
./sim.sh qstatus
./sim.sh pull                                # results/, REPORT.md, DESIGNS.md and the design records
python match.py results/runs/<hash>/S4P.s4p
```

`purpose` says why a run was made and ends up in its design record. The result cache key is the case content
plus `runner.MODEL`, bump MODEL when `sim_board.py` changes the physics or the outputs.

The server's i9-10900K is memory-bandwidth bound at about 113 MCells/s in total, whatever the split into
parallel runs. A search run has about 2 M cells, a 1.8e-13 s timestep and takes about 10 min alone on 20
threads or about 50 min when 6 runs share the machine.

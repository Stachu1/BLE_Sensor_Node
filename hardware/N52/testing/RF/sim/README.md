# BSN-N52 MIFA simulations (openEMS)

Moved here on 2026-11-23 from the separate AirTag project, where `BSN-N52-A` was designed as "AirTag". The text
below is the log as written then: "AirTag" and `AirTag.kicad_pcb` mean this board (`hardware/N52/BSN-N52.kicad_pcb`
now, three folders up), `library/AirTag.pretty` is `hardware/N52/library/BSN-N52.pretty`. The scripts were updated to
the new paths. The server work dir stays `~/openems_compute/airtag` so the cached runs remain valid. Large field
dumps (`report_r7/data`, `report_r7/work_final`, about 3 GB) and `build/` were not copied into the repo.

Scripted pipeline from a board (synthetic now, `AirTag.kicad_pcb` once the outline exists) to openEMS on the
compute server, for comparing meandered inverted-F antennas (MIFA) by size, match and efficiency. It is the
BLE_Sensor_Node C23 pipeline (`hardware/C23/testing/RF/sim`) reworked for a parametric MIFA on any board outline.

**Results:** `results/DESIGNS.md` ranks every simulated design, `results/designs/<run>/summary.md` holds the
record of each (purpose, parameters, KiCad position, drawing, impedance, ideal matching estimate, efficiency).

## Generic footprint (place this now)

`library/AirTag.pretty/MIFA_2G4.kicad_mod` (`python gen_mifa_footprint.py --generic`) fixes the board side of the
antenna before it is tuned:

- origin = feed point on the ground edge, antenna towards -y (KiCad), ground +y
- **keep-out 24 x 5 mm on every copper layer** (the full PCB width), from 5 mm left of the feed to 19 mm right of it
  (`antenna.GENERIC_KEEPOUT`), copper stays 0.3 mm inside it and 0.4 mm from the board edge
- feed notch 1 x 1 mm below the feed (tracks allowed): the feed trace and the L-match start at its bottom
- pad 1 feed, pad 2 short to ground (net tie), copper under solder mask

The copper inside is the untuned start geometry. Tuning (`tune.py`, cases with `"keepout"` in the antenna dict)
only moves copper inside the keep-out, the sims cut exactly this box from the board, and
`gen_mifa_footprint.py --run <hash>` writes the tuned copper into the same footprint. So the board layout around it
never changes: update the footprint from the library in KiCad and re-export.

Placement: ground pour right up to the keep-out on the sides and below, the 5 mm side away from the ground, ideally
along a board edge. Board edge closer than 0.4 mm to the copper is flagged by the sims.

**Matching:** the MIFA's peak feed resistance is well above 50 ohm on a board this small (smoke test: about 600 ohm
at S 1.6), so plan an L network at the notch bottom. `match_ideal.py` tries both orientations, series first and
shunt first (shunt on the antenna side, the usual one for R above 50 ohm). Pi pads (shunt, series, shunt, 0402)
leave both orientations open, fit two parts. Then add a port at those pads (like J2 in BSN) and simulate the real
parts before ordering.

## Model

- **Antenna** (`antenna.py`): one family `mifa`. Feed leg and short leg up from the ground edge, an arm, then `n`
  meander fingers between the arm height `H` and `G` above the ground edge, pitch `P`, trace width `W`.
  `n` is continuous (3.4 = 3 full fingers and 40 % of a fourth), `n = 0` is a plain IFA with the arm ending at
  `A`. Built in a local frame and placed at a **site** (feed point on the ground edge, rotation in steps of 90°,
  mirror). The geometry rules (gaps, notch, 0.4 mm to the board edge) are checked against the board outline.
- **Board:** `board.json` from `synth_board.py` (disc or rounded rectangle, 2 or 4 layers, all ground below the
  ground edge, via fence, CR1632 holder) or from `export_board.py` (the KiCad file, all copper layers, stack-up from
  the file or FR4 defaults, site from the AE1 footprint). Copper is zero-thickness metal.
- **Keep-out:** board copper inside the antenna bounding box + `K` and in the feed notch is removed on every layer
  in the sim (thin dielectric boxes at a higher priority than the board copper). Any antenna fits any board without
  a new export. Checked: notch built into the ground polygon vs cut by the boxes, see the smoke test below.
- **Port:** 50 Ω lumped port across the feed notch (`Nd` deep), from the notch bottom (ground) to the foot of the
  feed leg. In the footprint pad 1 fills the notch and the feed trace arrives at the notch bottom, so that is the
  reference plane. There is no matching network or test connector on the board yet. When there is, add a port at
  its pads (like J2 in the BSN pipeline) and model the real parts.
- **Battery:** the cell and the holder are electrically part of the circuit (user, 2026-11-14): the − contact is on
  GND, the + clip on VDD, and VDD is tied to the ground at RF by the decoupling caps and by the cell's own
  capacitance (+ can to − cap). Both terminals carry RF current and radiate, so they are never modelled as an
  isolated piece of metal. Model: CR1632 as one 16 mm metal cylinder 0.2 mm off the board on the BT1 side (+ and −
  joined), centred between the + clip pads, a contact block from every − pad to it (r2 has 3), the + clip as two
  straps standing on the + pads and a 0.2 mm bar over the far face. Parts are not modelled, so the VDD copper reaches
  the ground only through this cell model: check with `draw_layers.py build/<rev>/board.json` that the − pads touch
  the ground copper and the + pads are where the clip lands. A cell 46 MHz shift (no cell vs cell) was seen on T1.
- **Efficiency and pattern:** own near-to-far-field transform (`farfield.py`, copied from BSN, the openEMS NF2FF
  is wrong for layered boards). Dipole bench on the server 2026-11-14: 102 % and 2.18 dBi (expect 100 %, 2.15 dBi).
- **Solder mask:** not modelled by default (`"mask": "explicit"` needs 20 µm cells). On the BSN IFA it moved the
  resonance down by 1 %, so tune to about 2.465 GHz without it.
- **Mesh:** 0.2 mm in the antenna window, 0.1 mm at the port, 0.6 mm on the board, 30 mm air, PML 8 outside.
  About 1.5 M cells for a 30 mm disc, about 12-15 min with 3-4 runs sharing the server.

## Files

| file | runs on | does |
|---|---|---|
| `antenna.py` | both | MIFA geometry, placement, rules, length and size |
| `synth_board.py` | both | synthetic test boards `build/<name>/board.json` |
| `export_board.py` | laptop, KiCad python | `AirTag.kicad_pcb` -> `build/<rev>/board.json`, site from AE1 |
| `gen_mifa_footprint.py` | laptop | KiCad footprint from the same rectangles (origin = feed point, keep-out, net tie, `Sim` property) |
| `sim_board.py` | server | builds and runs one case, writes `result.json`, `S11.csv`, `pattern.npz` |
| `runner.py` | server | case lists in parallel, result cache by case content (`MODEL` in the key) |
| `tune.py` | server | tunes every candidate of a list to a target frequency (length parameter, optionally `S` for the match) |
| `queue.sh` | server | job queue within a thread budget (from BSN) |
| `make_cases.py` | laptop | grid of parameters -> case list (drops combinations that break the rules) |
| `draw_antennas.py` | laptop | drawing of every antenna of a case list on its board (KiCad coordinates) |
| `match_ideal.py` | laptop | worst BLE S11 with the best ideal 1- and 2-part match at the feed (from BSN), `--shift 1.01` for the mask |
| `make_board_copy.py` | laptop, KiCad python | copy of the board with GND pours, vias and another AE1 (boards/<name>/), for experiments |
| `plot_s11_compare.py` | laptop | S11 and Z of several runs in one plot, BLE shaded |
| `feedport.py` | both | the "trace" port on a routed feed trace (sub-ports across the trace gaps next to L1) |
| `draw_layers.py` | laptop | copper of every layer as exported, vias, BT1 pads with nets, cell outline (what is connected in the model) |
| `report.py` | laptop | design records and `results/DESIGNS.md` |
| `check_efficiency.py` | server | dipole reference check of the far-field code |
| `sim.sh` | laptop | `export`, `push`, `run`, `tune`, `queue`, `qstatus`, `status`, `bench`, `pull` |

## Use

```bash
python synth_board.py build/disc30 --d 30 --clear 6 --site -3          # a test board (or ./sim.sh export <rev>)
python make_cases.py cases/x.json --board build/disc30/board.json --grid H=3,4,5 --base '{"P": 1.2}' \
    --tune n --match S --purpose "why"
python draw_antennas.py cases/x.json        # look at results/plots/x_geometry.png first
./sim.sh tune cases/x.json 5 4              # or: ./sim.sh run / ./sim.sh queue
./sim.sh status
./sim.sh pull                               # results/, DESIGNS.md, design records
python gen_mifa_footprint.py --run <hash>   # footprint library/AirTag.pretty/MIFA_2G4.kicad_mod from a run
```

Every case-list item has `name`, `purpose` (why the run was made, shown in its record) and `case`
(`board`, `antenna`, optional `battery`, `mask`, `er_scale`, `tand_scale`, `nf2ff`, `mesh`, `keep_fields`).

When the board exists: place the footprint as AE1 with its origin on the ground edge, `./sim.sh export b1`, then
cases with `"board": "build/b1/board.json"` take the site from AE1 (a case can still move it with `"site"`).
Export every board change into a new `build/<rev>/`: the cache key holds the board path, not its content.

## Results on the real board (night of 2026-11-14, board copies in boards/)

The user's AirTag.kicad_pcb (24 x 24 mm, 2 layers, 1.6 mm, CR1632 on the back) was only read. `make_board_copy.py`
made copies with GND pours on both layers, a GND via grid and fence, and a different AE1, exported to build/b1..b7.
All runs: port across the feed notch (reference plane = notch bottom), cell fitted, no solder mask, target
2.465 GHz for the S11 minimum (2.44 + 1 % mask shift). Worst BLE = worst S11 over 2.400-2.4835 GHz after dividing the
simulated frequency by 1.01 (`match_ideal.py --shift 1.01`).

| copy | feed (KiCad) | keep-out | antenna | S11 min | -10 dB band | worst BLE, no parts / ideal 2-part L |
|---|---|---|---|---|---|---|
| b1 | 146, 93 | 24 x 5 | IFA + 1-2 folds (corner) | -9.7 dB | none | about -5 / -8.4 dB |
| b5 | 143, 92 | 24 x 4 | straight, H3.2 (not tuned) | -10.8 dB | 34 MHz | -3.5 / -8.3 dB |
| b4 | 143, 93 | 24 x 5 | straight H4.5 W0.5 A16.33 | -13.3 dB | 75 MHz | -9.5 / -10.2 dB |
| b4 | 143, 93 | 24 x 5 | **H4.6 W1.0 S1.25 A15.4 n0.17 = MIFA_2G4_T1** | -18.5 dB | 88 MHz | -9.5 / -10.5 dB |
| b6 | 143, 94 | 24 x 6 | straight H5.6 W0.5 A15.95 | -15.9 dB | 98 MHz | -9.7 / -11.3 dB |
| b6 | 143, 94 | 24 x 6 | **H5.6 W1.0 S1.25 A15.4 n0.04 = MIFA_2G4_T1_K6** | -24.6 dB | 101 MHz | -11.3 / -11.6 dB (shift 1.007) |

- The antenna is near 50 ohm by itself (Z at the S11 minimum 40-46 ohm, -11 to -17 j). A matching network does not
  help (about 1 dB at best with ideal parts): the -10 dB band is about as wide as BLE, so the antenna Q is the limit.
  Perfectly centred, the best worst-BLE is -10.4 dB (T1) and -10.9 dB (6 mm), within a centring window of only
  0.2-0.6 %, smaller than the er / mask uncertainty. Expect -9 to -10 dB at the band edges (0.5 dB mismatch loss),
  more if the real board lands off frequency.
- Keep-out height buys bandwidth (4 / 5 / 6 mm: 34 / 75 / 98 MHz), 1 mm traces buy some (68 -> 88 MHz at 4.6 mm),
  larger S hurts (S 1.5: 62 MHz, R at the minimum 32 ohm).
- From the feed at x 146 a straight arm runs into the rounded corner before it is long enough, the folded versions
  never reach -10 dB. The feed has to move to x 143 (3 mm left of L1).
- Radiation efficiency (own NF2FF, battery bias not removed) 1.02-1.08, i.e. about 95-100 % after the BSN battery
  calibration (x 1/1.09), Dmax about 1.9 dBi. Treat as +-15 %.
- `results/plots/keepout_height_s11.png`, `results/plots/finalists_s11.png` (plot_s11_compare.py),
  `results/plots/b7_check_geometry.png` (MIFA_2G4_T1 footprint copper = sim copper).
- Robustness of MIFA_2G4_T1 (cases/robust1.json, worst BLE with --shift 1.01, no parts / ideal 2-part L):

  | case | S11 min at | worst BLE |
  |---|---|---|
  | nominal (a21ed6f324) | 2.459 GHz | -9.5 / -10.5 dB |
  | FR4 er x0.96 (1b132cdadc) | 2.485 GHz (+26 MHz) | -7.9 / -10.7 dB |
  | FR4 er x1.04 (2b431274e2) | 2.434 GHz (-25 MHz) | -6.6 / -10.4 dB |
  | no CR1632 (ae0ce58148) | 2.413 GHz (-46 MHz) | -4.7 / -10.0 dB |
  | explicit 20 um mask (bb3d76116f, no shift) | 2.441 GHz (-18 MHz, -0.73 %) | **-10.2** / -10.4 dB |

  The match is not needed on the nominal board but recovers -10 dB when the board lands off frequency, so keep an
  L footprint (series + shunt, 0402) at the notch bottom, fitted 0R / DNP, tuned on the real board. The cell
  shifts the antenna by 46 MHz: measure with the cell fitted. The enclosure (not modelled) will move it down too.
- The explicit mask moved T1 by -0.73 % (BSN: -1 %). The 2.465 GHz tuner target is therefore about 6 MHz high, T1
  (tuned to 2.459) landed on the BLE centre with the mask. Use --shift 1.007 for scoring on this board.
- Footprints in library/AirTag.pretty: MIFA_2G4_T1 (AE1 at (143.0, 93.0)) and MIFA_2G4_T1_K6 (6 mm keep-out, AE1 at
  (143.0, 94.0)), both checked against the sim copper (results/plots/b7_check_geometry.png, b8_check_geometry.png).
  S11 of both and the mask run: results/plots/t1_vs_k6_s11.png.
- Edge rule: the arm top may come 0.4 mm from the board edge (EDGE_MARGIN), so with the ground edge 5 mm below the
  top edge H is at most 4.6 mm, and the top right corner limits the arm end to about A 15.95 at that height.

## Lessons carried over from BSN (see the pcb-antenna-sim skill)

- Bump `runner.MODEL` whenever `sim_board.py` or `antenna.py` change the physics or the outputs.
- Ideal parts at the feed are optimistic: finish with real pads, trace and lossy parts before naming parts.
- Throughput is memory-bandwidth bound (about 113 MCells/s in total on the server), split runs freely.
- The port must touch metal at both ends. On a real board the pour keeps its clearance from the feed pad, so the
  notch bottom was 0.25 mm lower than the footprint notch and every real-board run read S11 -0.2 dB (2026-11-14).
  sim_board.py now adds a copper tab from the notch bottom into the ground (antenna.port_tab_rect) and warns when S11
  never drops below -1 dB.
- openEMS drops metal it cannot use with only a warning. A zero-thickness clip strap on (or 0.2 mm off) the cell
  face was dropped ("Unused primitive", cause not found), now a solid bar. Read the run logs for that warning.
- **A routed feed trace breaks the notch port** (r2, 2026-11-14): the trace runs up to the antenna in its own gap of
  the pour, so the port tab at the notch bottom landed on the trace, not on the ground, and the port drove the
  antenna against a floating stub. Eight r2 runs were stopped. Boards with a routed feed trace use `"ports":
  "trace"` (feedport.py: two 100 ohm sub-ports across the trace gaps next to the end of the matching network, L1).
  Then no notch is needed in the model: the trace's own clearance gap in the pour is the feed gap, and the
  impedance is the one the matching network sees, trace included. Always zoom on the feed (draw_antennas.py zoom
  panel) after a new export.
- Do not tune a MIFA to the peak of R (metric Rmax): on these boards Rmax is 150-900 ohm and never approaches 50.
  Tune the S11 minimum (metric S11min) with S at its minimum.
- sim_board.py refuses an antenna that fails antenna.check, even by 0.001 mm (0.399 mm edge clearance), check
  every start point with ant.check on the exported board before starting a tuner.

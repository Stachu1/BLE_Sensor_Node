# C23 rev B antenna recommendation

Status 2026-11-03 evening. Based on the openEMS runs in this folder (records in [DESIGNS.md](DESIGNS.md)).
Numbers are simulation results with ideal matching parts unless a line says otherwise.

## Antenna to order

IFA on the b2 layout (L4 removed, via fence and ground fill 1.4 mm lower, ground edge at KiCad y 90.4).
Footprint `IFA_2G4_B2` in `hardware/C23/library/BSN-C23.pretty`, made with

    python gen_ifa_footprint.py --sim '{"S":3.5,"Ws":2,"Wf":1,"H":5.0,"Wa":1,"L":9.0}' --name IFA_2G4_B2

Place it with its origin on AE1 (KiCad 144.1, 90.225). `IFA_2G4` is untouched.

| part | KiCad x | KiCad y | width |
|---|---|---|---|
| short leg | 139.6 .. 141.6 | 84.4 .. ground | 2 mm |
| feed leg (AE1) | 143.6 .. 144.6 | 85.4 .. notch | 1 mm |
| arm | 139.6 .. 159.0 | 84.4 .. 85.4 | 1 mm |

Arm 5 mm above the ground edge, 0.75 mm from the nearest board edge. Antenna copper stays under solder mask.

## Matching

The antenna is tuned so its own resonance sits above the band (2.59 GHz with the mask modelled).
Then one shunt inductor on L3 matches the whole band and L2 stays 0R.

| case | resonance | worst BLE channel, no parts | 1 part (L3) | 2 parts (L2 + L3) |
|---|---|---|---|---|
| as built, 20 um mask modelled ([cae851224d](designs/cae851224d/summary.md)) | 2.588 GHz | -5.8 dB | -15.3 dB, 3.5 nH | -15.3 dB |
| no mask ([7d3b8b589d](designs/7d3b8b589d/summary.md)) | 2.607 GHz | -5.3 dB | -12.3 dB, 3.5 nH | -14.9 dB |
| no mask, finer mesh | 2.619 GHz | -5.0 dB | -10.0 dB, 3.75 nH | -15.2 dB, L2 0.58 nH |
| no mask, FR4 er -5 % | 2.634 GHz | -4.7 dB | -8.9 dB, 4.0 nH | -15.3 dB, L2 0.78 nH |
| no mask, FR4 er +5 % | 2.582 GHz | -6.0 dB | -14.3 dB, 4.5 nH | -14.3 dB |
| no mask, no battery | 2.602 GHz | -5.5 dB | -12.9 dB, 3.5 nH | -15.5 dB |

What this means for the bench:

- Start with L2 = 0R and L3 = 3.5 nH (3.3 nH or 3.6 nH in the E-series). The sim says about -15 dB in the whole band.
- If the board resonates higher than the sim (thin mask, lower er), a small series inductor on L2 (0.5 to 1 nH) plus about 3.9 nH on L3 gets back to about -15 dB. So keep both L2 and L3 pads and order a few values around these.
- Suggested parts for the tuning kit (0402 RF inductors): L3 3.0, 3.3, 3.6, 3.9, 4.3, 4.7 nH and L2 0.5, 0.8, 1.0, 1.2 nH plus 0R.
- The resonance tolerance from the inputs I know is about +-30 MHz (er +-5 % gives +-26 MHz, the mesh about +12 MHz, the battery about 5 MHz, the mask -19 MHz is already in the as-built row).

The E-series table from the 3-port run (real part values with their tolerance) is added below once that run finishes.

## Efficiency and pattern

- Radiation efficiency 85 to 95 % in the band, from the own far-field transform after calibration. The transform is validated to about +-15 %, so this says "no large loss", not an exact number.
- Peak directivity about 2 dBi, near-omni pattern with two shallow nulls of about -7 dB. Plots in each design record.

## Would a bigger board help

Yes, a bigger ground is the strongest lever left. Same antenna (H5.0), arm length re-tuned:

| board | worst BLE channel, no parts | 1 part | 2 parts |
|---|---|---|---|
| 34 x 34 mm (this board) | -5.8 dB | -15.3 dB | -15.3 dB |
| 5 mm taller | -7.0 dB | -16.2 dB | -17.7 dB |
| 10 mm taller | -9.5 dB | -17.6 dB | -19.8 dB |
| 4 mm wider | -8.7 dB | -16.0 dB | -17.4 dB |
| 8 mm wider | -15.3 dB (L9.0 run) | -20.5 dB (L9.2 run, 9.5 nH) | -20.5 dB |

Making the board 8 mm wider (in the antenna direction) gives a match better than -10 dB with no parts at all.
For a beacon, -10 dB already loses only 0.5 dB, and -15 dB loses 0.14 dB. So the 34 x 34 mm board with one inductor is
already close to what matching can give, and a bigger board mostly buys margin against tolerance.

Re-tuned arm lengths on the bigger boards (size3 batch) are running and will be added here.

## What was tried and did not help

- Wider arm, wider short leg, bent or folded end (FIFA): no wider band on this board.
- Arm height is the main lever, and H5.0 is the highest that fits under the top edge with the margin.

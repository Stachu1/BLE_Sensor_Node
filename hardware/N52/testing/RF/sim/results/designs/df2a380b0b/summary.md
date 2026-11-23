# df2a380b0b  r6 fold-back D2.5

**Purpose:** Board r6 = AirTag.kicad_pcb of 2026-11-14 23:46: L1 moved 0.75 mm up against the AE1 feed pad (feed trace in the pour almost gone), 7 vias moved. Matching parts are allowed now (user 2026-11-14): the antenna is scored by its Q and by match_tee.py (L2-C1-L1 T network, real 0402 parts, power into the antenna, >= 20 dB harmonic rejection). Base a63681b23e (S1.425 Ws2 Wf0.25 R5.5, Q 32, best T: worst channel -1.25 dB). Variant: return row 2.5 mm below the arm instead of 1.5 mm: less coupling between the opposite currents in arm and return row. Lower Q?

## Antenna

`fmifa S=1.425 H=4.6 A=12.4 D=2.5 R=5.5 W=1  (15.3 x 4.6 mm, L 25.9 mm)`

| parameter | value |
|---|---|
| W | 1 |
| Wf | 0.25 |
| Ws | 2 |
| S | 1.425 |
| H | 4.6 |
| A | 12.4 |
| D | 2.5 |
| R | 5.5 |
| Nd | 1 |
| Nw | 0 |
| K | 1 |
| site | {"x": -4.0, "y": 3.55, "rot": 0, "mirror": false} |

Copper 15.32 x 4.60 mm above the ground edge (70.5 mm2), centre-line length 25.9 mm.
KiCad position of the copper: x 143.57..158.90, y 91.55..96.40, edge clearance 0.40 mm.

![geometry](geometry.png)

## Impedance at the feed (port across the notch)

| | |
|---|---|
| S11 minimum | -13.8 dB at 2.136 GHz |
| Z at 2.44 GHz | 1.2 +38.3j ohm |
| -10 dB band | 2.118-2.154 GHz |
| worst BLE S11, no parts | -0.2 dB |
| worst BLE S11, best ideal 1 part | -0.6 dB (shunt 1.60 pF) |
| worst BLE S11, best ideal 2 parts | -3.3 dB (series 2.48 pF, shunt 5.10 pF) |

Ideal lossless parts right at the feed, listed from the antenna toward the chip (shunt first = shunt on the antenna side). Real parts on pads with a trace and Q 30-50 give less (BSN: -15.3 dB ideal became -10.9 dB).

![S11](s11.png)

## Efficiency (raw own far-field transform, about +-10 %)

| f (GHz) | radiation eff. | total eff. (no match) | Dmax (dBi) |
|---|---|---|---|
| 2.40 | 64 % | 4 % | 1.7 |
| 2.44 | 58 % | 3 % | 1.8 |
| 2.48 | 57 % | 3 % | 1.8 |

## Run

board `build/r6/board.json`, battery True, mask none, model m3, 1921866 cells, 2946 s.

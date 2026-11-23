# 2dbe6d660b  r4 fold-back W1.0 D1.5 it0

**Purpose:** Board r4 (AirTag.kicad_pcb of 2026-11-14 15:53: 24 x 17 mm, GND pours on both layers, AE1 at (146, 96.15), keep-out 20 x 5 mm (x 142..162) from the user-edited footprint, no notch, L1 right below the feed pad). Port beside the L1 feed pad (end of the matching network), so the result is what the network sees with no extra parts. S11 minimum tuned to 2.460 GHz. Variant: fold-back arm, 1 mm traces, return row 0.5 mm below the arm, return length R tuned.

## Antenna

`fmifa S=1.25 H=4.6 A=12.4 D=1.5 R=3 W=1  (14.7 x 4.6 mm, L 22.2 mm)`

| parameter | value |
|---|---|
| W | 1 |
| Wf | 0.5 |
| Ws | 1 |
| S | 1.25 |
| H | 4.6 |
| A | 12.4 |
| D | 1.5 |
| R | 3 |
| Nd | 1 |
| Nw | 1 |
| K | 1 |
| site | {"x": -4.0, "y": 3.55, "rot": 0, "mirror": false} |

Copper 14.65 x 4.60 mm above the ground edge (67.4 mm2), centre-line length 22.2 mm.
KiCad position of the copper: x 144.25..158.90, y 91.55..96.40, edge clearance 0.40 mm.

![geometry](geometry.png)

## Impedance at the feed (port across the notch)

| | |
|---|---|
| S11 minimum | -11.2 dB at 2.532 GHz |
| Z at 2.44 GHz | 10.4 +75.5j ohm |
| -10 dB band | 2.523-2.541 GHz |
| worst BLE S11, no parts | -0.6 dB |
| worst BLE S11, best ideal 1 part | -1.7 dB (series 1.00 pF) |
| worst BLE S11, best ideal 2 parts | -5.1 dB (series 1.47 pF, shunt 1.89 pF) |

Ideal lossless parts right at the feed, listed from the antenna toward the chip (shunt first = shunt on the antenna side). Real parts on pads with a trace and Q 30-50 give less (BSN: -15.3 dB ideal became -10.9 dB).

![S11](s11.png)

## Efficiency (raw own far-field transform, about +-10 %)

| f (GHz) | radiation eff. | total eff. (no match) | Dmax (dBi) |
|---|---|---|---|
| 2.40 | 30 % | 4 % | 2.6 |
| 2.44 | 33 % | 7 % | 2.6 |
| 2.48 | 40 % | 17 % | 2.6 |

## Run

board `build/r4/board.json`, battery True, mask none, model m3, 2016384 cells, 3950 s.

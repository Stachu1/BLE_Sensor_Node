# 1d7585b9c4  r7 final ref normal mesh + mask

**Purpose:** Final check 2026-11-15 (r7). Normal x/y mesh with the explicit 20 um solder mask on both sides: mask shift on r7, and the reference for the high-resolution run.

## Antenna

`fmifa S=1.825 H=4.6 A=12.4 D=1.5 R=5.5 W=1  (15.7 x 4.6 mm, L 25.3 mm)`

| parameter | value |
|---|---|
| W | 1 |
| Wf | 0.5 |
| Ws | 2 |
| S | 1.825 |
| H | 4.6 |
| A | 12.4 |
| D | 1.5 |
| R | 5.5 |
| Nd | 1 |
| Nw | 0 |
| K | 1 |
| site | {"x": -4.0, "y": 3.55, "rot": 0, "mirror": false} |

Copper 15.72 x 4.60 mm above the ground edge (72.3 mm2), centre-line length 25.3 mm.
KiCad position of the copper: x 143.18..158.90, y 91.55..96.40, edge clearance 0.40 mm.

![geometry](geometry.png)

## Impedance at the feed (port across the notch)

| | |
|---|---|
| S11 minimum | -8.3 dB at 2.492 GHz |
| Z at 2.44 GHz | 100.3 -72.0j ohm |
| -10 dB band | - |
| worst BLE S11, no parts | -3.3 dB |
| worst BLE S11, best ideal 1 part | -3.3 dB (series 3.00 pF) |
| worst BLE S11, best ideal 2 parts | -6.8 dB (shunt 5.25 nH, series 1.18 pF) |

Ideal lossless parts right at the feed, listed from the antenna toward the chip (shunt first = shunt on the antenna side). Real parts on pads with a trace and Q 30-50 give less (BSN: -15.3 dB ideal became -10.9 dB).

![S11](s11.png)

## Efficiency (raw own far-field transform, about +-10 %)

| f (GHz) | radiation eff. | total eff. (no match) | Dmax (dBi) |
|---|---|---|---|
| 2.40 | 67 % | 35 % | 1.7 |
| 2.44 | 67 % | 49 % | 1.7 |
| 2.48 | 69 % | 58 % | 1.7 |

## Run

board `build/r7/board.json`, battery True, mask explicit, model m3, 3199328 cells, 16362 s.

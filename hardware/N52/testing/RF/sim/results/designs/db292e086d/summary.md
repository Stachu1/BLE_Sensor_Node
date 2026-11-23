# db292e086d  r5 fold-back S1.55 Ws2 Wf0.5 it1

**Purpose:** r5 S1.55 Ws2.0 (00308fa64b): Rmax 219 ohm, best match -11.2 dB at 2.639 GHz (Z 39-23j) above the resonance. Lengthen the return row R so this match point moves to 2.460 GHz.

## Antenna

`fmifa S=1.55 H=4.6 A=12.4 D=1.5 R=5.4835 W=1  (15.4 x 4.6 mm, L 25.0 mm)`

| parameter | value |
|---|---|
| W | 1 |
| Wf | 0.5 |
| Ws | 2 |
| S | 1.55 |
| H | 4.6 |
| A | 12.4 |
| D | 1.5 |
| R | 5.4835 |
| Nd | 1 |
| Nw | 0 |
| K | 1 |
| site | {"x": -4.0, "y": 3.55, "rot": 0, "mirror": false} |

Copper 15.45 x 4.60 mm above the ground edge (71.1 mm2), centre-line length 25.0 mm.
KiCad position of the copper: x 143.45..158.90, y 91.55..96.40, edge clearance 0.40 mm.

![geometry](geometry.png)

## Impedance at the feed (port across the notch)

| | |
|---|---|
| S11 minimum | -10.5 dB at 2.502 GHz |
| Z at 2.44 GHz | 176.0 -25.2j ohm |
| -10 dB band | 2.491-2.513 GHz |
| worst BLE S11, no parts | -2.7 dB |
| worst BLE S11, best ideal 1 part | -4.0 dB (series 1.30 pF) |
| worst BLE S11, best ideal 2 parts | -6.7 dB (shunt 8.09 nH, series 1.09 pF) |

Ideal lossless parts right at the feed, listed from the antenna toward the chip (shunt first = shunt on the antenna side). Real parts on pads with a trace and Q 30-50 give less (BSN: -15.3 dB ideal became -10.9 dB).

![S11](s11.png)

## Efficiency (raw own far-field transform, about +-10 %)

| f (GHz) | radiation eff. | total eff. (no match) | Dmax (dBi) |
|---|---|---|---|
| 2.40 | 72 % | 33 % | 1.6 |
| 2.44 | 74 % | 50 % | 1.6 |
| 2.48 | 75 % | 65 % | 1.7 |

## Run

board `build/r5/board.json`, battery True, mask none, model m3, 2004992 cells, 2324 s.

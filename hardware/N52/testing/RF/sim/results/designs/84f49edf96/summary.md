# 84f49edf96  n4

**Purpose:** Smoke test of the AirTag pipeline (synthetic 30 mm disc board, CR1632 on the bottom)

## Antenna

`mifa S=1.6 H=4 A=2.4 G=1 n=4 P=1.2 W=0.5  (8.1 x 4.0 mm, L 21.3 mm)`

| parameter | value |
|---|---|
| W | 0.5 |
| Wf | 0.5 |
| Ws | 0.5 |
| S | 1.6 |
| H | 4 |
| A | 2.4 |
| G | 1 |
| n | 4 |
| P | 1.2 |
| Nd | 1 |
| Nw | 1.5 |
| K | 1 |
| site | {"x": -3.0, "y": 9.0, "rot": 0, "mirror": false} |

Copper 8.10 x 4.00 mm above the ground edge (32.4 mm2), centre-line length 21.3 mm.
KiCad position of the copper: x 145.15..153.25, y 87.00..91.25, edge clearance 1.12 mm.

![geometry](geometry.png)

## Impedance at the feed (port across the notch)

| | |
|---|---|
| S11 minimum | -8.1 dB at 3.400 GHz |
| Z at 2.44 GHz | 4.1 +126.2j ohm |
| -10 dB band | - |
| worst BLE S11, no parts | -0.2 dB |
| worst BLE S11, best ideal 1 part | -0.2 dB (shunt 0.55 pF) |
| worst BLE S11, best ideal 2 parts | -3.5 dB (series 0.61 pF, shunt 3.15 pF) |

Ideal parts sit right at the feed. Real parts on pads with a trace and Q 30-50 give less, see the BSN lessons.

![S11](s11.png)

## Efficiency (raw own far-field transform, about +-10 %)

| f (GHz) | radiation eff. | total eff. (no match) | Dmax (dBi) |
|---|---|---|---|
| 2.40 | 82 % | 3 % | 1.7 |
| 2.44 | 82 % | 4 % | 1.7 |
| 2.48 | 81 % | 4 % | 1.8 |

## Run

board `build/disc30/board.json`, battery True, mask none, model m1, 1594404 cells, 814 s.

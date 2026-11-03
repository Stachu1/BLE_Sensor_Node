# bent_h40 fifa S=3.5 Ws=1 Wf=1 H=4 Wa=0.8 L=10.4 H2=2.4 L2=0.8

**Why this run:** Tuner start points: bent-end IFA with the arm 4 mm above the ground edge (b1).

Run `9e819c48ec`, tag `tune_bent_h40`, model v4, board `build/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

fifa, ground edge base b1: S 3.5 mm, Ws 1 mm, Wf 1 mm, H 4 mm, Wa 0.8 mm, L 10.4 mm, H2 2.4 mm, L2 0.8 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 140.10 | 84.20 | 141.10 | 89.25 |
| feed leg | 143.60 | 85.00 | 144.60 | 90.00 |
| arm | 140.10 | 84.20 | 160.40 | 85.00 |
| drop | 159.60 | 84.20 | 160.40 | 86.60 |
| return | 159.60 | 85.80 | 160.40 | 86.60 |

Copper extent x 140.10..160.40, y 84.20..90.00 (KiCad), smallest distance to the board edge 0.57 mm.

## Impedance and match at J2

Best match without parts -6.4 dB at 2.351 GHz, worst BLE channel -4.8 dB, -10 dB band none MHz.

Z at J2: 2.40 GHz 23.9+29.6j ohm, 2.44 GHz 28.8+42.5j ohm, 2.48 GHz 36.0+57.7j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -4.8 dB |
| 1 part: shunt 0.80 pF | -7.0 dB |
| 2 parts: series 3.74 pF, shunt 0.94 pF | -11.8 dB |

![s11](s11.png)

## Efficiency and pattern

Not valid: this run used the openEMS NF2FF transform (model v4), which is wrong for this board.

Mesh 2021136 cells, run time 98 min.

# size2 b2w4 H5.0 L9.2

**Why this run:** Bigger board combined with the best 34 mm design (arm H5.0 L9.2): does the board-size gain add to the arm-height gain?

Run `c9a183a68e`, tag `size2`, model v5, board `build/b2w4/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b2w4: S 3.5 mm, Ws 2 mm, Wf 1 mm, H 5 mm, Wa 1 mm, L 9.2 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.60 | 84.40 | 141.60 | 90.65 |
| feed leg | 143.60 | 85.40 | 144.60 | 91.22 |
| arm | 139.60 | 84.40 | 159.20 | 85.40 |

Copper extent x 139.60..159.20, y 84.40..91.22 (KiCad), smallest distance to the board edge 0.75 mm.

## Impedance and match at J2

Best match without parts -20.2 dB at 2.537 GHz, worst BLE channel -8.7 dB, -10 dB band [2421, 2673] MHz.

Z at J2: 2.40 GHz 31.6-25.2j ohm, 2.44 GHz 33.9-16.4j ohm, 2.48 GHz 36.8-7.7j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -8.7 dB |
| 1 part: shunt 7.25 nH | -16.0 dB |
| 2 parts: series 10.37 pF, shunt 4.94 nH | -17.4 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 89 % | 77 % | 1.9 |
| 2.44 | 90 % | 84 % | 2.0 |
| 2.48 | 91 % | 88 % | 2.0 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 2044224 cells, run time 36 min.

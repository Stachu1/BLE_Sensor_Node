# size2 b2t5 H5.0 L9.2

**Why this run:** Bigger board combined with the best 34 mm design (arm H5.0 L9.2): does the board-size gain add to the arm-height gain?

Run `55cfd9813c`, tag `size2`, model v5, board `build/b2t5/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b2t5: S 3.5 mm, Ws 2 mm, Wf 1 mm, H 5 mm, Wa 1 mm, L 9.2 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.60 | 84.40 | 141.60 | 90.65 |
| feed leg | 143.60 | 85.40 | 144.60 | 91.22 |
| arm | 139.60 | 84.40 | 159.20 | 85.40 |

Copper extent x 139.60..159.20, y 84.40..91.22 (KiCad), smallest distance to the board edge 0.75 mm.

## Impedance and match at J2

Best match without parts -21.7 dB at 2.588 GHz, worst BLE channel -7.0 dB, -10 dB band [2461, 2734] MHz.

Z at J2: 2.40 GHz 30.6-34.0j ohm, 2.44 GHz 32.3-25.6j ohm, 2.48 GHz 34.4-17.5j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -7.0 dB |
| 1 part: shunt 4.00 nH | -16.2 dB |
| 2 parts: series 0.19 nH, shunt 4.80 nH | -17.7 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 88 % | 71 % | 2.2 |
| 2.44 | 89 % | 78 % | 2.2 |
| 2.48 | 90 % | 83 % | 2.3 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 2059668 cells, run time 34 min.

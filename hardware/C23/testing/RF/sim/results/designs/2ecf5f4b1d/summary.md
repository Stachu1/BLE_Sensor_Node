# size2 b2w8 H5.0 L9.2

**Why this run:** Bigger board combined with the best 34 mm design (arm H5.0 L9.2): does the board-size gain add to the arm-height gain?

Run `2ecf5f4b1d`, tag `size2`, model v5, board `build/b2w8/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b2w8: S 3.5 mm, Ws 2 mm, Wf 1 mm, H 5 mm, Wa 1 mm, L 9.2 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.60 | 84.40 | 141.60 | 90.65 |
| feed leg | 143.60 | 85.40 | 144.60 | 91.22 |
| arm | 139.60 | 84.40 | 159.20 | 85.40 |

Copper extent x 139.60..159.20, y 84.40..91.22 (KiCad), smallest distance to the board edge 0.75 mm.

## Impedance and match at J2

Best match without parts -36.9 dB at 2.516 GHz, worst BLE channel -11.7 dB, -10 dB band [2375, 2690] MHz.

Z at J2: 2.40 GHz 41.2-22.7j ohm, 2.44 GHz 44.0-14.9j ohm, 2.48 GHz 47.4-7.3j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -11.7 dB |
| 1 part: shunt 9.50 nH | -20.5 dB |
| 2 parts: shunt 9.50 nH | -20.5 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 91 % | 85 % | 2.0 |
| 2.44 | 92 % | 90 % | 2.1 |
| 2.48 | 93 % | 92 % | 2.1 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 2105064 cells, run time 35 min.

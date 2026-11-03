# final1 H5.0 L9.0 no battery

**Why this run:** Final candidate without the CR2032: the first bench measurement is likely done without the battery

Run `a07042320a`, tag `final2`, model v5, board `build/b2/board.json`, battery no, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b2: S 3.5 mm, Ws 2 mm, Wf 1 mm, H 5 mm, Wa 1 mm, L 9 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.60 | 84.40 | 141.60 | 90.65 |
| feed leg | 143.60 | 85.40 | 144.60 | 91.22 |
| arm | 139.60 | 84.40 | 159.00 | 85.40 |

Copper extent x 139.60..159.00, y 84.40..91.22 (KiCad), smallest distance to the board edge 0.75 mm.

## Impedance and match at J2

Best match without parts -16.3 dB at 2.602 GHz, worst BLE channel -5.5 dB, -10 dB band [2498, 2719] MHz.

Z at J2: 2.40 GHz 25.0-36.8j ohm, 2.44 GHz 26.6-27.8j ohm, 2.48 GHz 28.6-19.2j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -5.5 dB |
| 1 part: shunt 3.50 nH | -12.9 dB |
| 2 parts: series 0.22 nH, shunt 3.64 nH | -15.5 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 87 % | 63 % | 1.9 |
| 2.44 | 88 % | 71 % | 1.9 |
| 2.48 | 89 % | 78 % | 1.9 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 1807920 cells, run time 31 min.

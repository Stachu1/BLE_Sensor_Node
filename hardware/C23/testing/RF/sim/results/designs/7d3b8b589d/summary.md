# final1 H5.0 L9.0

**Why this run:** Final candidate H5.0 L9.0 (one shunt inductor on L3, mask-corrected length): nominal, no mask

Run `7d3b8b589d`, tag `final1`, model v5, board `build/b2/board.json`, battery yes, mask none.

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

Best match without parts -16.0 dB at 2.607 GHz, worst BLE channel -5.3 dB, -10 dB band [2504, 2723] MHz.

Z at J2: 2.40 GHz 24.7-37.6j ohm, 2.44 GHz 26.1-28.7j ohm, 2.48 GHz 28.0-20.1j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -5.3 dB |
| 1 part: shunt 3.50 nH | -12.3 dB |
| 2 parts: series 0.36 nH, shunt 4.21 nH | -14.9 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 87 % | 61 % | 2.0 |
| 2.44 | 88 % | 70 % | 2.0 |
| 2.48 | 89 % | 77 % | 2.0 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 1971216 cells, run time 35 min.

# final1 H5.0 L9.0 er+5%

**Why this run:** Final candidate H5.0 L9.0 (one shunt inductor on L3, mask-corrected length): FR4 permittivity 5 % high (board tolerance)

Run `09fc7f9410`, tag `final1`, model v5, board `build/b2/board.json`, battery yes, mask none, er x1.05.

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

Best match without parts -14.8 dB at 2.582 GHz, worst BLE channel -6.0 dB, -10 dB band [2485, 2689] MHz.

Z at J2: 2.40 GHz 23.8-30.4j ohm, 2.44 GHz 25.6-21.8j ohm, 2.48 GHz 27.9-13.3j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -6.0 dB |
| 1 part: shunt 4.50 nH | -14.3 dB |
| 2 parts: shunt 4.50 nH | -14.3 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 87 % | 65 % | 2.0 |
| 2.44 | 88 % | 73 % | 2.0 |
| 2.48 | 89 % | 79 % | 2.0 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 1971216 cells, run time 35 min.

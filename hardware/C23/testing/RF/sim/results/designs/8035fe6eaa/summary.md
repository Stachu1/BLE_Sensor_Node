# b2c H5.0 L9.2 (arm 0.6 higher)

**Why this run:** Candidates on b2 around the best quick result (arm top at KiCad y 85): length, short-leg spacing, arm width, arm height.

Run `8035fe6eaa`, tag `b2_cand1`, model v5, board `build/b2/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b2: S 3.5 mm, Ws 2 mm, Wf 1 mm, H 5 mm, Wa 1 mm, L 9.2 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.60 | 84.40 | 141.60 | 90.65 |
| feed leg | 143.60 | 85.40 | 144.60 | 91.22 |
| arm | 139.60 | 84.40 | 159.20 | 85.40 |

Copper extent x 139.60..159.20, y 84.40..91.22 (KiCad), smallest distance to the board edge 0.75 mm.

## Impedance and match at J2

Best match without parts -15.3 dB at 2.585 GHz, worst BLE channel -5.9 dB, -10 dB band [2486, 2694] MHz.

Z at J2: 2.40 GHz 25.1-33.5j ohm, 2.44 GHz 26.6-24.5j ohm, 2.48 GHz 28.7-15.7j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -5.9 dB |
| 1 part: shunt 3.75 nH | -15.4 dB |
| 2 parts: shunt 3.75 nH | -15.4 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 87 % | 65 % | 2.0 |
| 2.44 | 88 % | 72 % | 2.0 |
| 2.48 | 89 % | 79 % | 2.0 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 1983384 cells, run time 54 min.

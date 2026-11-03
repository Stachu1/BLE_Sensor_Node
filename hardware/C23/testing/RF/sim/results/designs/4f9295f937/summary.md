# b2c top 85 Wa2 H3.4 L9.7

**Why this run:** Candidates on b2 around the best quick result (arm top at KiCad y 85): length, short-leg spacing, arm width, arm height.

Run `4f9295f937`, tag `b2_cand1`, model v5, board `build/b2/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b2: S 3.5 mm, Ws 2 mm, Wf 1 mm, H 3.4 mm, Wa 2 mm, L 9.7 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.60 | 85.00 | 141.60 | 90.65 |
| feed leg | 143.60 | 87.00 | 144.60 | 91.22 |
| arm | 139.60 | 85.00 | 159.70 | 87.00 |

Copper extent x 139.60..159.70, y 85.00..91.22 (KiCad), smallest distance to the board edge 1.31 mm.

## Impedance and match at J2

Best match without parts -9.0 dB at 2.459 GHz, worst BLE channel -8.2 dB, -10 dB band none MHz.

Z at J2: 2.40 GHz 23.5-11.1j ohm, 2.44 GHz 23.7-1.8j ohm, 2.48 GHz 24.2+7.2j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -8.2 dB |
| 1 part: shunt 39.75 nH | -8.5 dB |
| 2 parts: series 2.80 pF, shunt 3.35 nH | -14.0 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 86 % | 73 % | 1.9 |
| 2.44 | 87 % | 76 % | 2.0 |
| 2.48 | 88 % | 77 % | 2.0 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 1970670 cells, run time 56 min.

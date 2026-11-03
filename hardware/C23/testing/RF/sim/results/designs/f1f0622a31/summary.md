# b2c H4.4 L9.7 S4.5

**Why this run:** Candidates on b2 around the best quick result (arm top at KiCad y 85): length, short-leg spacing, arm width, arm height.

Run `f1f0622a31`, tag `b2_cand1`, model v5, board `build/b2/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b2: S 4.5 mm, Ws 2 mm, Wf 1 mm, H 4.4 mm, Wa 1 mm, L 9.7 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 138.60 | 85.00 | 140.60 | 90.65 |
| feed leg | 143.60 | 86.00 | 144.60 | 91.22 |
| arm | 138.60 | 85.00 | 159.70 | 86.00 |

Copper extent x 138.60..159.70, y 85.00..91.22 (KiCad), smallest distance to the board edge 0.87 mm.

## Impedance and match at J2

Best match without parts -9.8 dB at 2.545 GHz, worst BLE channel -6.4 dB, -10 dB band none MHz.

Z at J2: 2.40 GHz 19.9-16.7j ohm, 2.44 GHz 21.6-8.8j ohm, 2.48 GHz 23.6-0.9j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -6.4 dB |
| 1 part: shunt 8.50 nH | -8.6 dB |
| 2 parts: series 4.16 pF, shunt 3.06 nH | -14.4 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 86 % | 66 % | 1.9 |
| 2.44 | 87 % | 72 % | 2.0 |
| 2.48 | 88 % | 76 % | 2.0 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 1970670 cells, run time 53 min.

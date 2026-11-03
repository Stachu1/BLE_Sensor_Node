# size b2t5, 5 mm taller

**Why this run:** Bigger board: how much does a larger ground plane improve the matched bandwidth and efficiency of the same IFA (H4.4 L9.7)?

Run `be4e12aea4`, tag `size1`, model v5, board `build/b2t5/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b2t5: S 3.5 mm, Ws 2 mm, Wf 1 mm, H 4.4 mm, Wa 1 mm, L 9.7 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.60 | 85.00 | 141.60 | 90.65 |
| feed leg | 143.60 | 86.00 | 144.60 | 91.22 |
| arm | 139.60 | 85.00 | 159.70 | 86.00 |

Copper extent x 139.60..159.70, y 85.00..91.22 (KiCad), smallest distance to the board edge 1.31 mm.

## Impedance and match at J2

Best match without parts -14.6 dB at 2.527 GHz, worst BLE channel -8.6 dB, -10 dB band [2427, 2639] MHz.

Z at J2: 2.40 GHz 29.3-22.5j ohm, 2.44 GHz 30.6-13.5j ohm, 2.48 GHz 32.3-4.7j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -8.6 dB |
| 1 part: shunt 8.75 nH | -13.3 dB |
| 2 parts: series 6.51 pF, shunt 4.46 nH | -16.6 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 87 % | 75 % | 2.2 |
| 2.44 | 88 % | 81 % | 2.2 |
| 2.48 | 89 % | 85 % | 2.2 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 2046954 cells, run time 48 min.

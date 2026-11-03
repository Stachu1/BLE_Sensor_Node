# size3 b2t10 H5.0 L8.6

**Why this run:** Bigger board at its best: arm length re-tuned for the larger ground (resonance moves down on a bigger board)

Run `f5d7b1da46`, tag `size3`, model v5, board `build/b2t10/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b2t10: S 3.5 mm, Ws 2 mm, Wf 1 mm, H 5 mm, Wa 1 mm, L 8.6 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.60 | 84.40 | 141.60 | 90.65 |
| feed leg | 143.60 | 85.40 | 144.60 | 91.22 |
| arm | 139.60 | 84.40 | 158.60 | 85.40 |

Copper extent x 139.60..158.60, y 84.40..91.22 (KiCad), smallest distance to the board edge 0.75 mm.

## Impedance and match at J2

Best match without parts -54.3 dB at 2.700 GHz, worst BLE channel -5.4 dB, -10 dB band [2532, 2878] MHz.

Z at J2: 2.40 GHz 34.0-49.7j ohm, 2.44 GHz 34.8-42.2j ohm, 2.48 GHz 36.0-35.1j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -5.4 dB |
| 1 part: shunt 4.75 nH | -8.8 dB |
| 2 parts: series 1.30 nH, shunt 5.23 nH | -19.2 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 89 % | 63 % | 2.5 |
| 2.44 | 90 % | 70 % | 2.5 |
| 2.48 | 90 % | 75 % | 2.6 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 2135952 cells, run time 42 min.

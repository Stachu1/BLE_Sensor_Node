# size3 b2w8t10 H5.0 L8.6

**Why this run:** Bigger board at its best: arm length re-tuned for the larger ground (resonance moves down on a bigger board)

Run `9cf2fece7a`, tag `size3`, model v5, board `build/b2w8t10/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b2w8t10: S 3.5 mm, Ws 2 mm, Wf 1 mm, H 5 mm, Wa 1 mm, L 8.6 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.60 | 84.40 | 141.60 | 90.65 |
| feed leg | 143.60 | 85.40 | 144.60 | 91.22 |
| arm | 139.60 | 84.40 | 158.60 | 85.40 |

Copper extent x 139.60..158.60, y 84.40..91.22 (KiCad), smallest distance to the board edge 0.75 mm.

## Impedance and match at J2

Best match without parts -21.7 dB at 2.644 GHz, worst BLE channel -7.5 dB, -10 dB band [2467, 2833] MHz.

Z at J2: 2.40 GHz 42.8-42.4j ohm, 2.44 GHz 44.0-35.5j ohm, 2.48 GHz 45.6-29.0j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -7.5 dB |
| 1 part: shunt 5.75 nH | -11.8 dB |
| 2 parts: series 1.33 nH, shunt 9.53 nH | -21.9 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 91 % | 75 % | 2.3 |
| 2.44 | 91 % | 80 % | 2.4 |
| 2.48 | 92 % | 84 % | 2.4 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 2266992 cells, run time 42 min.

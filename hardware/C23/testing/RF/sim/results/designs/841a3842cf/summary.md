# size3 b2w8 H5.0 L9.6

**Why this run:** Bigger board at its best: arm length re-tuned for the larger ground (resonance moves down on a bigger board)

Run `841a3842cf`, tag `size3`, model v5, board `build/b2w8/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b2w8: S 3.5 mm, Ws 2 mm, Wf 1 mm, H 5 mm, Wa 1 mm, L 9.6 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.60 | 84.40 | 141.60 | 90.65 |
| feed leg | 143.60 | 85.40 | 144.60 | 91.22 |
| arm | 139.60 | 84.40 | 159.60 | 85.40 |

Copper extent x 139.60..159.60, y 84.40..91.22 (KiCad), smallest distance to the board edge 0.75 mm.

## Impedance and match at J2

Best match without parts -36.0 dB at 2.466 GHz, worst BLE channel -16.1 dB, -10 dB band [2335, 2626] MHz.

Z at J2: 2.40 GHz 42.6-12.7j ohm, 2.44 GHz 46.0-4.4j ohm, 2.48 GHz 50.3+3.6j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -16.1 dB |
| 1 part: shunt 26.75 nH | -19.8 dB |
| 2 parts: series 9.10 pF, shunt 12.75 nH | -20.1 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 92 % | 89 % | 2.0 |
| 2.44 | 93 % | 92 % | 2.1 |
| 2.48 | 93 % | 93 % | 2.1 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 2105064 cells, run time 45 min.

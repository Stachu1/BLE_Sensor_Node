# b2h H5.0 L9.5

**Why this run:** Push the arm higher (height is the main lever for the matched band). Self-resonance aimed at about 2.58 GHz so one shunt inductor on L3 matches the band.

Run `517f44192f`, tag `b2_high1`, model v5, board `build/b2/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b2: S 3.5 mm, Ws 2 mm, Wf 1 mm, H 5 mm, Wa 1 mm, L 9.5 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.60 | 84.40 | 141.60 | 90.65 |
| feed leg | 143.60 | 85.40 | 144.60 | 91.22 |
| arm | 139.60 | 84.40 | 159.50 | 85.40 |

Copper extent x 139.60..159.50, y 84.40..91.22 (KiCad), smallest distance to the board edge 0.75 mm.

## Impedance and match at J2

Best match without parts -14.4 dB at 2.550 GHz, worst BLE channel -6.9 dB, -10 dB band [2460, 2650] MHz.

Z at J2: 2.40 GHz 25.8-27.0j ohm, 2.44 GHz 27.6-17.8j ohm, 2.48 GHz 29.9-8.7j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -6.9 dB |
| 1 part: shunt 6.00 nH | -13.1 dB |
| 2 parts: series 10.29 pF, shunt 3.90 nH | -15.5 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 87 % | 69 % | 2.0 |
| 2.44 | 88 % | 77 % | 2.0 |
| 2.48 | 89 % | 82 % | 2.0 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 1971216 cells, run time 43 min.

# b2h H5.5 S3 Ws1 L8.9

**Why this run:** Push the arm higher (height is the main lever for the matched band). Self-resonance aimed at about 2.58 GHz so one shunt inductor on L3 matches the band.

Run `054ed6a4ea`, tag `b2_high1`, model v5, board `build/b2/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b2: S 3 mm, Ws 1 mm, Wf 1 mm, H 5.5 mm, Wa 1 mm, L 8.9 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 140.60 | 83.90 | 141.60 | 90.65 |
| feed leg | 143.60 | 84.90 | 144.60 | 91.22 |
| arm | 140.60 | 83.90 | 158.90 | 84.90 |

Copper extent x 140.60..158.90, y 83.90..91.22 (KiCad), smallest distance to the board edge 0.59 mm.

## Impedance and match at J2

Best match without parts -16.5 dB at 2.615 GHz, worst BLE channel -5.3 dB, -10 dB band [2506, 2739] MHz.

Z at J2: 2.40 GHz 22.6-33.7j ohm, 2.44 GHz 24.4-25.8j ohm, 2.48 GHz 26.7-18.1j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -5.3 dB |
| 1 part: shunt 3.25 nH | -14.6 dB |
| 2 parts: series 0.18 nH, shunt 3.94 nH | -15.0 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 88 % | 62 % | 2.0 |
| 2.44 | 89 % | 70 % | 2.0 |
| 2.48 | 90 % | 77 % | 2.0 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 1983384 cells, run time 44 min.

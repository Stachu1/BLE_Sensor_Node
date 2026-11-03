# b2h H5.0 S2.5 L9.2

**Why this run:** Push the arm higher (height is the main lever for the matched band). Self-resonance aimed at about 2.58 GHz so one shunt inductor on L3 matches the band.

Run `20f93f358f`, tag `b2_high1`, model v5, board `build/b2/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b2: S 2.5 mm, Ws 2 mm, Wf 1 mm, H 5 mm, Wa 1 mm, L 9.2 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 140.60 | 84.40 | 142.60 | 90.65 |
| feed leg | 143.60 | 85.40 | 144.60 | 91.22 |
| arm | 140.60 | 84.40 | 159.20 | 85.40 |

Copper extent x 140.60..159.20, y 84.40..91.22 (KiCad), smallest distance to the board edge 1.07 mm.

## Impedance and match at J2

Best match without parts -19.8 dB at 2.561 GHz, worst BLE channel -6.2 dB, -10 dB band [2465, 2669] MHz.

Z at J2: 2.40 GHz 36.8-46.6j ohm, 2.44 GHz 36.8-33.3j ohm, 2.48 GHz 37.4-21.1j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -6.2 dB |
| 1 part: shunt 5.00 nH | -10.1 dB |
| 2 parts: series 0.86 nH, shunt 6.33 nH | -15.2 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 86 % | 66 % | 1.9 |
| 2.44 | 87 % | 74 % | 2.0 |
| 2.48 | 88 % | 82 % | 2.0 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 1995552 cells, run time 45 min.

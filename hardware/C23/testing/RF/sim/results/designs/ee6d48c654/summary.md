# final1 H5.0 L9.0 mask 3-port

**Why this run:** Final candidate H5.0 L9.0 (one shunt inductor on L3, mask-corrected length): 3-port (J2, L2, L3) with explicit mask for the real L2/L3 parts table

Run `ee6d48c654`, tag `final1_3port`, model v5, board `build/b2/board.json`, battery yes, mask explicit.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b2: S 3.5 mm, Ws 2 mm, Wf 1 mm, H 5 mm, Wa 1 mm, L 9 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.60 | 84.40 | 141.60 | 90.65 |
| feed leg | 143.60 | 85.40 | 144.60 | 91.22 |
| arm | 139.60 | 84.40 | 159.00 | 85.40 |

Copper extent x 139.60..159.00, y 84.40..91.22 (KiCad), smallest distance to the board edge 0.75 mm.

## Impedance and match at J2

Best match without parts -30.7 dB at 1.955 GHz, worst BLE channel -12.4 dB, -10 dB band [1900, 3000] MHz.

Z at J2: 2.40 GHz 31.8-3.6j ohm, 2.44 GHz 31.1-2.1j ohm, 2.48 GHz 30.6-0.6j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -12.4 dB |
| 1 part: shunt 39.75 nH | -12.4 dB |
| 2 parts: series 2.93 pF, shunt 4.25 nH | -29.4 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 14 % | 13 % | 1.9 |
| 2.44 | 14 % | 14 % | 1.9 |
| 2.48 | 15 % | 14 % | 2.0 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 3736286 cells, run time 209 min.

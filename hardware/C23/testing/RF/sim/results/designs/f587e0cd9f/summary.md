# cal b2 H4.4 L9.7 lossless no battery

**Why this run:** Efficiency calibration without the battery (separates the battery from the method bias).

Run `f587e0cd9f`, tag `cal1`, model v5, board `build/b2/board.json`, battery no, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b2: S 3.5 mm, Ws 2 mm, Wf 1 mm, H 4.4 mm, Wa 1 mm, L 9.7 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.60 | 85.00 | 141.60 | 90.65 |
| feed leg | 143.60 | 86.00 | 144.60 | 91.22 |
| arm | 139.60 | 85.00 | 159.70 | 86.00 |

Copper extent x 139.60..159.70, y 85.00..91.22 (KiCad), smallest distance to the board edge 1.31 mm.

## Impedance and match at J2

Best match without parts -9.9 dB at 2.526 GHz, worst BLE channel -6.3 dB, -10 dB band none MHz.

Z at J2: 2.40 GHz 21.1-21.8j ohm, 2.44 GHz 22.6-12.1j ohm, 2.48 GHz 24.3-2.5j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -6.3 dB |
| 1 part: shunt 8.25 nH | -9.1 dB |
| 2 parts: series 5.25 pF, shunt 3.32 nH | -13.3 dB |

![s11](s11.png)

## Efficiency and pattern

| f GHz | radiation eff. | total eff. (no parts) | Dmax dBi |
|---|---|---|---|
| 2.40 | 100 % | 77 % | 1.9 |
| 2.44 | 100 % | 83 % | 1.9 |
| 2.48 | 100 % | 88 % | 1.9 |

Own far-field transform, about ±15 % (validation in farfield.py). Total efficiency is without matching parts.

![pattern](pattern.png)

Mesh 1796256 cells, run time 31 min.

# ifa_h30 ifa S=3.5 Ws=2 Wf=1 H=3 Wa=1 L=11.9

**Why this run:** Tuner start points: straight IFA with the arm 3 mm above the ground edge (b1), tuning L and S towards 50 ohm at J2.

Run `3dc287e066`, tag `tune_ifa_h30`, model v4, board `build/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b1: S 3.5 mm, Ws 2 mm, Wf 1 mm, H 3 mm, Wa 1 mm, L 11.9 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.60 | 85.00 | 141.60 | 89.25 |
| feed leg | 143.60 | 86.00 | 144.60 | 90.00 |
| arm | 139.60 | 85.00 | 161.90 | 86.00 |

Copper extent x 139.60..161.90, y 85.00..90.00 (KiCad), smallest distance to the board edge 0.62 mm.

## Impedance and match at J2

Best match without parts -5.7 dB at 2.294 GHz, worst BLE channel -3.5 dB, -10 dB band none MHz.

Z at J2: 2.40 GHz 18.5+31.2j ohm, 2.44 GHz 20.6+42.8j ohm, 2.48 GHz 23.7+55.5j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -3.5 dB |
| 1 part: shunt 0.95 pF | -5.7 dB |
| 2 parts: series 3.82 pF, shunt 1.30 pF | -10.8 dB |

![s11](s11.png)

## Efficiency and pattern

Not valid: this run used the openEMS NF2FF transform (model v4), which is wrong for this board.

Mesh 1970670 cells, run time 99 min.

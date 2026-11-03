# ifa_h25 ifa S=4 Ws=2 Wf=1 H=2.5 Wa=1 L=11.8

**Why this run:** Tuner start points: straight IFA with the arm 2.5 mm above the ground edge (b1).

Run `34f2bd6780`, tag `tune_ifa_h25`, model v4, board `build/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b1: S 4 mm, Ws 2 mm, Wf 1 mm, H 2.5 mm, Wa 1 mm, L 11.8 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.10 | 85.50 | 141.10 | 89.25 |
| feed leg | 143.60 | 86.50 | 144.60 | 90.00 |
| arm | 139.10 | 85.50 | 161.80 | 86.50 |

Copper extent x 139.10..161.80, y 85.50..90.00 (KiCad), smallest distance to the board edge 1.10 mm.

## Impedance and match at J2

Best match without parts -4.3 dB at 2.275 GHz, worst BLE channel -2.9 dB, -10 dB band none MHz.

Z at J2: 2.40 GHz 14.1+30.9j ohm, 2.44 GHz 15.5+40.9j ohm, 2.48 GHz 17.6+51.8j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -2.9 dB |
| 1 part: shunt 1.10 pF | -5.1 dB |
| 2 parts: series 4.12 pF, shunt 1.60 pF | -9.8 dB |

![s11](s11.png)

## Efficiency and pattern

Not valid: this run used the openEMS NF2FF transform (model v4), which is wrong for this board.

Mesh 1970670 cells, run time 96 min.

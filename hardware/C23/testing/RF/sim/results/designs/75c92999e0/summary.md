# ifa_h25 ifa S=3.5 Ws=2 Wf=1 H=2.5 Wa=1 L=12.4

**Why this run:** Tuner start points: straight IFA with the arm 2.5 mm above the ground edge (b1).

Run `75c92999e0`, tag `tune_ifa_h25`, model v4, board `build/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b1: S 3.5 mm, Ws 2 mm, Wf 1 mm, H 2.5 mm, Wa 1 mm, L 12.4 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.60 | 85.50 | 141.60 | 89.25 |
| feed leg | 143.60 | 86.50 | 144.60 | 90.00 |
| arm | 139.60 | 85.50 | 162.40 | 86.50 |

Copper extent x 139.60..162.40, y 85.50..90.00 (KiCad), smallest distance to the board edge 0.76 mm.

## Impedance and match at J2

Best match without parts -4.7 dB at 2.203 GHz, worst BLE channel -2.2 dB, -10 dB band none MHz.

Z at J2: 2.40 GHz 14.7+45.6j ohm, 2.44 GHz 16.4+56.7j ohm, 2.48 GHz 18.7+68.7j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -2.2 dB |
| 1 part: shunt 0.85 pF | -3.2 dB |
| 2 parts: series 2.10 pF, shunt 1.49 pF | -9.3 dB |

![s11](s11.png)

## Efficiency and pattern

Not valid: this run used the openEMS NF2FF transform (model v4), which is wrong for this board.

Mesh 1958580 cells, run time 99 min.

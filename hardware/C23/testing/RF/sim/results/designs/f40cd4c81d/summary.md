# ifa_h30 ifa S=4 Ws=2 Wf=1 H=3 Wa=1 L=11.3

**Why this run:** Tuner start points: straight IFA with the arm 3 mm above the ground edge (b1), tuning L and S towards 50 ohm at J2.

Run `f40cd4c81d`, tag `tune_ifa_h30`, model v4, board `build/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b1: S 4 mm, Ws 2 mm, Wf 1 mm, H 3 mm, Wa 1 mm, L 11.3 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.10 | 85.00 | 141.10 | 89.25 |
| feed leg | 143.60 | 86.00 | 144.60 | 90.00 |
| arm | 139.10 | 85.00 | 161.30 | 86.00 |

Copper extent x 139.10..161.30, y 85.00..90.00 (KiCad), smallest distance to the board edge 0.92 mm.

## Impedance and match at J2

Best match without parts -5.5 dB at 2.372 GHz, worst BLE channel -4.6 dB, -10 dB band none MHz.

Z at J2: 2.40 GHz 16.9+16.4j ohm, 2.44 GHz 18.6+26.1j ohm, 2.48 GHz 21.1+36.7j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -4.6 dB |
| 1 part: shunt 1.35 pF | -11.3 dB |
| 2 parts: shunt 1.35 pF | -11.3 dB |

![s11](s11.png)

## Efficiency and pattern

Not valid: this run used the openEMS NF2FF transform (model v4), which is wrong for this board.

Mesh 1970670 cells, run time 96 min.

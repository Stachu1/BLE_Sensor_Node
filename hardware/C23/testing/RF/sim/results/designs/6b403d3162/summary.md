# ifa_h25 ifa S=3.5 Ws=2 Wf=1 H=2.5 Wa=1 L=11.8

**Why this run:** Tuner start points: straight IFA with the arm 2.5 mm above the ground edge (b1).

Run `6b403d3162`, tag `tune_ifa_h25`, model v4, board `build/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

ifa, ground edge base b1: S 3.5 mm, Ws 2 mm, Wf 1 mm, H 2.5 mm, Wa 1 mm, L 11.8 mm

| part | KiCad x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| short leg | 139.60 | 85.50 | 141.60 | 89.25 |
| feed leg | 143.60 | 86.50 | 144.60 | 90.00 |
| arm | 139.60 | 85.50 | 161.80 | 86.50 |

Copper extent x 139.60..161.80, y 85.50..90.00 (KiCad), smallest distance to the board edge 1.10 mm.

## Impedance and match at J2

Best match without parts -4.8 dB at 2.263 GHz, worst BLE channel -2.8 dB, -10 dB band none MHz.

Z at J2: 2.40 GHz 14.4+31.1j ohm, 2.44 GHz 15.6+41.4j ohm, 2.48 GHz 17.3+52.2j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -2.8 dB |
| 1 part: shunt 1.10 pF | -5.0 dB |
| 2 parts: series 3.94 pF, shunt 1.62 pF | -9.8 dB |

![s11](s11.png)

## Efficiency and pattern

Not valid: this run used the openEMS NF2FF transform (model v4), which is wrong for this board.

Mesh 1970670 cells, run time 99 min.

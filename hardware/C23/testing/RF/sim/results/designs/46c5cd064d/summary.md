# placed_lossless

**Why this run:** Reference: AE1 as first placed on the rev B board (b1), with explicit solder mask and with lossless FR4 to measure the mask shift and the FR4 loss.

Run `46c5cd064d`, tag `ref`, model v4, board `build/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

placed (AE1 copper from the board file)

Copper extent x 139.60..159.10, y 85.00..90.00 (KiCad), smallest distance to the board edge 1.31 mm.

## Impedance and match at J2

Best match without parts -6.9 dB at 2.666 GHz, worst BLE channel -2.8 dB, -10 dB band none MHz.

Z at J2: 2.40 GHz 12.5-37.6j ohm, 2.44 GHz 13.2-29.1j ohm, 2.48 GHz 14.0-21.1j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -2.8 dB |
| 1 part: shunt 2.75 nH | -7.3 dB |
| 2 parts: series 0.40 nH, shunt 2.27 nH | -10.4 dB |

![s11](s11.png)

## Efficiency and pattern

Not valid: this run used the openEMS NF2FF transform (model v4), which is wrong for this board.

Mesh 1983384 cells, run time 86 min.

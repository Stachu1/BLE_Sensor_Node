# placed

**Why this run:** Reference: AE1 as first placed on the rev B board (b1), with explicit solder mask and with lossless FR4 to measure the mask shift and the FR4 loss.

Run `2c86f6e332`, tag `ref`, model v4, board `build/board.json`, battery yes, mask none.

![geometry](geometry.png)

## Antenna

placed (AE1 copper from the board file)

Copper extent x 139.60..159.10, y 85.00..90.00 (KiCad), smallest distance to the board edge 1.31 mm.

## Impedance and match at J2

Best match without parts -8.0 dB at 2.659 GHz, worst BLE channel -3.5 dB, -10 dB band none MHz.

Z at J2: 2.40 GHz 16.0-37.2j ohm, 2.44 GHz 16.4-28.8j ohm, 2.48 GHz 17.0-20.8j ohm

| matching (ideal parts at J2, L2 series, L3 shunt) | worst BLE S11 |
|---|---|
| none (L2 0R) | -3.5 dB |
| 1 part: shunt 3.00 nH | -9.3 dB |
| 2 parts: series 0.36 nH, shunt 2.27 nH | -11.8 dB |

![s11](s11.png)

## Efficiency and pattern

Not valid: this run used the openEMS NF2FF transform (model v4), which is wrong for this board.

Mesh 1983384 cells, run time 86 min.

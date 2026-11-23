# c6c1fddafe  IFA H4.5 W0.5 it1

**Purpose:** Can the antenna reach 50 ohm without a matching network inside the 24 x 5 mm keep-out (full PCB width, user 2026-11-14)? Synthetic board matching AirTag.kicad_pcb as of 2026-11-14 (24 x 24 mm outline, 2 layers 1.6 mm, CR1632 on the back at BT1 (150, 109), overhanging the bottom edge as laid out, no pours yet so all ground below the keep-out), AE1 feed at (143, 93): keep-out = full width, top edge. Tuned: arm length to 2.465 GHz and S towards Rmax 50 ohm. Variant: straight IFA, the generic start.

## Antenna

`mifa S=1.5 H=4.5 A=13.3853 G=1 n=0 P=1 W=0.5  (15.1 x 4.5 mm, L 19.1 mm)`

| parameter | value |
|---|---|
| W | 0.5 |
| Wf | 0.5 |
| Ws | 0.5 |
| S | 1.5 |
| H | 4.5 |
| A | 13.3853 |
| G | 1 |
| n | 0 |
| P | 1 |
| Nd | 1 |
| Nw | 1 |
| K | 1 |
| site | {"x": -7.0, "y": 7.0, "rot": 0, "mirror": false} |

Copper 15.13 x 4.50 mm above the ground edge (68.1 mm2), centre-line length 19.1 mm.
KiCad position of the copper: x 141.25..156.39, y 88.50..93.25, edge clearance 0.50 mm.

![geometry](geometry.png)

## Impedance at the feed (port across the notch)

| | |
|---|---|
| S11 minimum | -13.0 dB at 2.835 GHz |
| Z at 2.44 GHz | 66.7 +229.2j ohm |
| -10 dB band | 2.776-2.896 GHz |
| worst BLE S11, no parts | -0.8 dB |
| worst BLE S11, best ideal 1 part | -5.8 dB (series 0.30 pF) |
| worst BLE S11, best ideal 2 parts | -8.3 dB (shunt 43.73 nH, series 0.41 pF) |

Ideal lossless parts right at the feed, listed from the antenna toward the chip (shunt first = shunt on the antenna side). Real parts on pads with a trace and Q 30-50 give less (BSN: -15.3 dB ideal became -10.9 dB).

![S11](s11.png)

## Efficiency (raw own far-field transform, about +-10 %)

| f (GHz) | radiation eff. | total eff. (no match) | Dmax (dBi) |
|---|---|---|---|
| 2.40 | 93 % | 15 % | 1.9 |
| 2.44 | 95 % | 19 % | 1.9 |
| 2.48 | 98 % | 24 % | 1.9 |

## Run

board `build/rect24/board.json`, battery True, mask none, model m2, 2209680 cells, 3570 s.

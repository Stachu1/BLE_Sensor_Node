# dfd660996a  b5 k4 H3.2 straight it0

**Purpose:** Keep-out height experiment, feed at (143, 92) like b4, the keep-out top stays at the board edge (KiCad y 88). Board copy b5 (sim/boards/b5: AirTag.kicad_pcb of 2026-11-14 01:21 with GND pours and a via fence, AE1 = MIFA_f143k4: 24 x 4 mm keep-out). b4 (24 x 5) straight IFA it0 gave S11 -14.4 dB at 2.551 GHz with Z 40-14j at the minimum and a 90 MHz -10 dB band. Does a 4 mm (lower) keep-out widen (or narrow) the matched band? S at its minimum, length tuned so the S11 minimum sits at 2.465 GHz. Variant: straight IFA, arm 3.2 mm high (max straight A 17.3, corner).

## Antenna

`mifa S=1 H=3.2 A=17 G=1 n=0 P=1 W=0.5  (18.2 x 3.2 mm, L 20.9 mm)`

| parameter | value |
|---|---|
| W | 0.5 |
| Wf | 0.5 |
| Ws | 0.5 |
| S | 1 |
| H | 3.2 |
| A | 17 |
| G | 1 |
| n | 0 |
| P | 1 |
| Nd | 1 |
| Nw | 1 |
| K | 1 |
| site | {"x": -7.0, "y": 8.0, "rot": 0, "mirror": false} |

Copper 18.25 x 3.20 mm above the ground edge (58.4 mm2), centre-line length 20.9 mm.
KiCad position of the copper: x 141.75..160.00, y 88.80..92.25, edge clearance 0.58 mm.

![geometry](geometry.png)

## Impedance at the feed (port across the notch)

| | |
|---|---|
| S11 minimum | -10.8 dB at 2.399 GHz |
| Z at 2.44 GHz | 21.8 -9.1j ohm |
| -10 dB band | 2.382-2.416 GHz |
| worst BLE S11, no parts | -4.6 dB |
| worst BLE S11, best ideal 1 part | -5.0 dB (shunt 0.95 pF) |
| worst BLE S11, best ideal 2 parts | -8.4 dB (series 1.80 nH, shunt 1.22 pF) |

Ideal lossless parts right at the feed, listed from the antenna toward the chip (shunt first = shunt on the antenna side). Real parts on pads with a trace and Q 30-50 give less (BSN: -15.3 dB ideal became -10.9 dB).

![S11](s11.png)

## Efficiency (raw own far-field transform, about +-10 %)

| f (GHz) | radiation eff. | total eff. (no match) | Dmax (dBi) |
|---|---|---|---|
| 2.40 | 87 % | 80 % | 1.9 |
| 2.44 | 91 % | 76 % | 1.9 |
| 2.48 | 95 % | 63 % | 1.9 |

## Run

board `build/b5/board.json`, battery True, mask none, model m3, 2091055 cells, 8183 s.

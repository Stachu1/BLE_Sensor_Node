# bbeffd3ab2  r5 fold-back it0 no battery

**Purpose:** Board r5 = AirTag.kicad_pcb of 2026-11-14 19:20 with the GND via stitching added by the user (57 vias, short-leg island stitched). Same without the CR1632 and holder: is the cell the second resonator that splits the r4v resonance?

## Antenna

`fmifa S=1.25 H=4.6 A=12.4 D=1.5 R=3 W=1  (14.7 x 4.6 mm, L 22.2 mm)`

| parameter | value |
|---|---|
| W | 1 |
| Wf | 0.5 |
| Ws | 1 |
| S | 1.25 |
| H | 4.6 |
| A | 12.4 |
| D | 1.5 |
| R | 3 |
| Nd | 1 |
| Nw | 1 |
| K | 1 |
| site | {"x": -4.0, "y": 3.55, "rot": 0, "mirror": false} |

Copper 14.65 x 4.60 mm above the ground edge (67.4 mm2), centre-line length 22.2 mm.
KiCad position of the copper: x 144.25..158.90, y 91.55..96.40, edge clearance 0.40 mm.

![geometry](geometry.png)

## Impedance at the feed (port across the notch)

| | |
|---|---|
| S11 minimum | -6.7 dB at 2.597 GHz |
| Z at 2.44 GHz | 314.0 +220.2j ohm |
| -10 dB band | - |
| worst BLE S11, no parts | -1.4 dB |
| worst BLE S11, best ideal 1 part | -2.2 dB (series 1.10 pF) |
| worst BLE S11, best ideal 2 parts | -6.1 dB (shunt 11.14 nH, series 0.62 pF) |

Ideal lossless parts right at the feed, listed from the antenna toward the chip (shunt first = shunt on the antenna side). Real parts on pads with a trace and Q 30-50 give less (BSN: -15.3 dB ideal became -10.9 dB).

![S11](s11.png)

## Efficiency (raw own far-field transform, about +-10 %)

| f (GHz) | radiation eff. | total eff. (no match) | Dmax (dBi) |
|---|---|---|---|
| 2.40 | 62 % | 17 % | 1.4 |
| 2.44 | 69 % | 24 % | 1.4 |
| 2.48 | 73 % | 34 % | 1.4 |

## Run

board `build/r5/board.json`, battery False, mask none, model m3, 1757525 cells, 1869 s.

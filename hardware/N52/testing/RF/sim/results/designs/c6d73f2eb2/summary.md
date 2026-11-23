# c6d73f2eb2  b1 S1.0 W0.5 A12 P1.0 it0

**Purpose:** Real board copy b1 (sim/boards/b1: AirTag.kicad_pcb of 2026-11-14 01:21 with GND pours and a via fence, AE1 = generic 24 x 5 keep-out, feed at (146, 93) above L1, port across the notch). Can it match 50 ohm without parts? The peak R cannot reach 50 ohm (keepout24 it1: 742 -> 412 ohm for S 2.5 -> 1.5) but the S11 minimum on the slope above the resonance deepens as S shrinks, so: S at its minimum, length tuned so the S11 MINIMUM sits at 2.465 GHz (2.44 + 1 % for the mask). Variant: IFA with 1-2 meander folds at the end (a straight arm does not fit right of the feed), 0.5 mm traces.

## Antenna

`mifa S=1 H=4.5 A=12 G=1 n=1.7 P=1 W=0.5  (14.5 x 4.5 mm, L 23.1 mm)`

| parameter | value |
|---|---|
| W | 0.5 |
| Wf | 0.5 |
| Ws | 0.5 |
| S | 1 |
| H | 4.5 |
| A | 12 |
| G | 1 |
| n | 1.7 |
| P | 1 |
| Nd | 1 |
| Nw | 1 |
| K | 1 |
| site | {"x": -4.0, "y": 7.0, "rot": 0, "mirror": false} |

Copper 14.50 x 4.50 mm above the ground edge (65.2 mm2), centre-line length 23.1 mm.
KiCad position of the copper: x 144.75..159.25, y 88.50..93.25, edge clearance 0.50 mm.

![geometry](geometry.png)

## Impedance at the feed (port across the notch)

| | |
|---|---|
| S11 minimum | -0.2 dB at 2.233 GHz |
| Z at 2.44 GHz | 36.5 -1096.3j ohm |
| -10 dB band | - |
| worst BLE S11, no parts | -0.0 dB |
| worst BLE S11, best ideal 1 part | -0.0 dB (series 14.80 nH) |
| worst BLE S11, best ideal 2 parts | -0.6 dB (shunt 12.93 nH, series 0.27 pF) |

Ideal lossless parts right at the feed, listed from the antenna toward the chip (shunt first = shunt on the antenna side). Real parts on pads with a trace and Q 30-50 give less (BSN: -15.3 dB ideal became -10.9 dB).

![S11](s11.png)

## Efficiency (raw own far-field transform, about +-10 %)

| f (GHz) | radiation eff. | total eff. (no match) | Dmax (dBi) |
|---|---|---|---|
| 2.40 | 40 % | 0 % | 1.9 |
| 2.44 | 34 % | 0 % | 1.9 |
| 2.48 | 28 % | 0 % | 1.9 |

## Run

board `build/b1/board.json`, battery True, mask none, model m2, 2168574 cells, 11292 s.

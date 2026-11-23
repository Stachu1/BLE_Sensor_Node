# b7d1a8bddf  b4 S1.0 W0.5 straight it2

**Purpose:** Real board copy b4 (sim/boards/b4: AirTag.kicad_pcb of 2026-11-14 01:21 with GND pours and a via fence, AE1 = MIFA_f143: 24 x 5 keep-out, feed at (143, 93), 5 mm from the left edge, port across the notch). Can it match 50 ohm without parts? The peak R cannot reach 50 ohm (keepout24 it1: 742 -> 412 ohm for S 2.5 -> 1.5) but the S11 minimum on the slope above the resonance deepens as S shrinks, so: S at its minimum, length tuned so the S11 MINIMUM sits at 2.465 GHz (2.44 + 1 % for the mask). Variant: straight IFA, fits because the feed is 3 mm further left.

## Antenna

`mifa S=1 H=4.5 A=16.3341 G=1 n=0 P=1.2 W=0.5  (17.6 x 4.5 mm, L 21.6 mm)`

| parameter | value |
|---|---|
| W | 0.5 |
| Wf | 0.5 |
| Ws | 0.5 |
| S | 1 |
| H | 4.5 |
| A | 16.3341 |
| G | 1 |
| n | 0 |
| P | 1.2 |
| Nd | 1 |
| Nw | 1 |
| K | 1 |
| site | {"x": -7.0, "y": 7.0, "rot": 0, "mirror": false} |

Copper 17.58 x 4.50 mm above the ground edge (79.1 mm2), centre-line length 21.6 mm.
KiCad position of the copper: x 141.75..159.33, y 88.50..93.25, edge clearance 0.48 mm.

![geometry](geometry.png)

## Impedance at the feed (port across the notch)

| | |
|---|---|
| S11 minimum | -13.3 dB at 2.466 GHz |
| Z at 2.44 GHz | 55.4 -28.8j ohm |
| -10 dB band | 2.429-2.504 GHz |
| worst BLE S11, no parts | -7.0 dB |
| worst BLE S11, best ideal 1 part | -8.7 dB (series 2.20 nH) |
| worst BLE S11, best ideal 2 parts | -10.1 dB (shunt 4.94 nH, series 2.28 pF) |

Ideal lossless parts right at the feed, listed from the antenna toward the chip (shunt first = shunt on the antenna side). Real parts on pads with a trace and Q 30-50 give less (BSN: -15.3 dB ideal became -10.9 dB).

![S11](s11.png)

## Efficiency (raw own far-field transform, about +-10 %)

| f (GHz) | radiation eff. | total eff. (no match) | Dmax (dBi) |
|---|---|---|---|
| 2.40 | 101 % | 81 % | 1.8 |
| 2.44 | 102 % | 94 % | 1.9 |
| 2.48 | 104 % | 98 % | 1.9 |

## Run

board `build/b4/board.json`, battery True, mask none, model m3, 2152020 cells, 3578 s.

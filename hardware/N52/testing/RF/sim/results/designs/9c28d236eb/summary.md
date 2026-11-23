# 9c28d236eb  b4 H4.6 W0.5 S1.5 it1

**Purpose:** Board copy b4 (feed at (143, 93), 24 x 5 keep-out, GND pours). b4 straight IFA (H4.5 W0.5 S1.0) it1 reached the target: S11 min -13.4 dB at 2.476 GHz but its -10 dB band is only 77 MHz (BLE needs 78), so the antenna Q is the limit. Variant: arm 4.6 mm high and S 1.5 (R at the minimum was 40 ohm, larger S raises it towards 50). Length tuned so the S11 minimum sits at 2.465 GHz.

## Antenna

`mifa S=1.5 H=4.6 A=15.95 G=1 n=0 P=1 W=0.5  (17.7 x 4.6 mm, L 21.8 mm)`

| parameter | value |
|---|---|
| W | 0.5 |
| Wf | 0.5 |
| Ws | 0.5 |
| S | 1.5 |
| H | 4.6 |
| A | 15.95 |
| G | 1 |
| n | 0 |
| P | 1 |
| Nd | 1 |
| Nw | 1 |
| K | 1 |
| site | {"x": -7.0, "y": 7.0, "rot": 0, "mirror": false} |

Copper 17.70 x 4.60 mm above the ground edge (81.4 mm2), centre-line length 21.8 mm.
KiCad position of the copper: x 141.25..158.95, y 88.40..93.25, edge clearance 0.40 mm.

![geometry](geometry.png)

## Impedance at the feed (port across the notch)

| | |
|---|---|
| S11 minimum | -10.8 dB at 2.519 GHz |
| Z at 2.44 GHz | 67.3 -61.3j ohm |
| -10 dB band | 2.495-2.545 GHz |
| worst BLE S11, no parts | -4.3 dB |
| worst BLE S11, best ideal 1 part | -7.3 dB (series 4.80 nH) |
| worst BLE S11, best ideal 2 parts | -9.8 dB (shunt 0.27 pF, series 3.53 nH) |

Ideal lossless parts right at the feed, listed from the antenna toward the chip (shunt first = shunt on the antenna side). Real parts on pads with a trace and Q 30-50 give less (BSN: -15.3 dB ideal became -10.9 dB).

![S11](s11.png)

## Efficiency (raw own far-field transform, about +-10 %)

| f (GHz) | radiation eff. | total eff. (no match) | Dmax (dBi) |
|---|---|---|---|
| 2.40 | 102 % | 64 % | 1.8 |
| 2.44 | 103 % | 79 % | 1.9 |
| 2.48 | 104 % | 91 % | 1.9 |

## Run

board `build/b4/board.json`, battery True, mask none, model m3, 2152020 cells, 4480 s.

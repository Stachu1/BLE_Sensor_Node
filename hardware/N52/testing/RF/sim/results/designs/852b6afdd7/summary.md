# 852b6afdd7  b4 H4.6 W1.0 S1.25 fold it0

**Purpose:** Board copy b4 (feed at (143, 93), 24 x 5 keep-out, GND pours). b4 straight IFA (H4.5 W0.5 S1.0) it1 reached the target: S11 min -13.4 dB at 2.476 GHz but its -10 dB band is only 77 MHz (BLE needs 78), so the antenna Q is the limit. Variant: arm 4.6 mm high and 1 mm wide traces (lower Q?). The corner limits a straight arm to A 15.95 at this height, so a short fold down at the end (n) is tuned so the S11 minimum sits at 2.465 GHz.

## Antenna

`mifa S=1.25 H=4.6 A=15.4 G=1 n=0.3 P=1 W=1  (17.6 x 4.6 mm, L 21.5 mm)`

| parameter | value |
|---|---|
| W | 1 |
| Wf | 0.5 |
| Ws | 1 |
| S | 1.25 |
| H | 4.6 |
| A | 15.4 |
| G | 1 |
| n | 0.3 |
| P | 1 |
| Nd | 1 |
| Nw | 1 |
| K | 1 |
| site | {"x": -7.0, "y": 7.0, "rot": 0, "mirror": false} |

Copper 17.65 x 4.60 mm above the ground edge (81.2 mm2), centre-line length 21.5 mm.
KiCad position of the copper: x 141.25..158.90, y 88.40..93.25, edge clearance 0.40 mm.

![geometry](geometry.png)

## Impedance at the feed (port across the notch)

| | |
|---|---|
| S11 minimum | -17.6 dB at 2.425 GHz |
| Z at 2.44 GHz | 37.0 -7.1j ohm |
| -10 dB band | 2.384-2.467 GHz |
| worst BLE S11, no parts | -8.0 dB |
| worst BLE S11, best ideal 1 part | -8.7 dB (shunt 0.50 pF) |
| worst BLE S11, best ideal 2 parts | -10.2 dB (series 3.36 pF, shunt 6.41 nH) |

Ideal lossless parts right at the feed, listed from the antenna toward the chip (shunt first = shunt on the antenna side). Real parts on pads with a trace and Q 30-50 give less (BSN: -15.3 dB ideal became -10.9 dB).

![S11](s11.png)

## Efficiency (raw own far-field transform, about +-10 %)

| f (GHz) | radiation eff. | total eff. (no match) | Dmax (dBi) |
|---|---|---|---|
| 2.40 | 101 % | 97 % | 1.9 |
| 2.44 | 104 % | 101 % | 1.9 |
| 2.48 | 108 % | 92 % | 1.9 |

## Run

board `build/b4/board.json`, battery True, mask none, model m3, 2146947 cells, 5272 s.

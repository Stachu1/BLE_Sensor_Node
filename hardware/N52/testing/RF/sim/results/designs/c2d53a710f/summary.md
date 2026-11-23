# c2d53a710f  r4 meander W1.0 P1.5 it0

**Purpose:** Board r4 (AirTag.kicad_pcb of 2026-11-14 15:53: 24 x 17 mm, GND pours on both layers, AE1 at (146, 96.15), keep-out 20 x 5 mm (x 142..162) from the user-edited footprint, no notch, L1 right below the feed pad). Port beside the L1 feed pad (end of the matching network), so the result is what the network sees with no extra parts. S11 minimum tuned to 2.460 GHz. Variant: meander end, 1 mm traces, pitch 1.5 mm, fingers 1 mm above the ground, n tuned.

## Antenna

`mifa S=1.25 H=4.6 A=12 G=1 n=1.5 P=1.5 W=1  (15.8 x 4.6 mm, L 22.0 mm)`

| parameter | value |
|---|---|
| W | 1 |
| Wf | 0.5 |
| Ws | 1 |
| S | 1.25 |
| H | 4.6 |
| A | 12 |
| G | 1 |
| n | 1.5 |
| P | 1.5 |
| Nd | 1 |
| Nw | 1 |
| K | 1 |
| site | {"x": -4.0, "y": 3.55, "rot": 0, "mirror": false} |

Copper 15.75 x 4.60 mm above the ground edge (72.5 mm2), centre-line length 22.0 mm.
KiCad position of the copper: x 144.25..160.00, y 91.55..96.40, edge clearance 0.40 mm.

![geometry](geometry.png)

## Impedance at the feed (port across the notch)

| | |
|---|---|
| S11 minimum | -12.6 dB at 2.493 GHz |
| Z at 2.44 GHz | 27.1 +82.9j ohm |
| -10 dB band | 2.482-2.504 GHz |
| worst BLE S11, no parts | -1.2 dB |
| worst BLE S11, best ideal 1 part | -3.6 dB (series 1.00 pF) |
| worst BLE S11, best ideal 2 parts | -6.5 dB (shunt 0.27 pF, series 0.83 pF) |

Ideal lossless parts right at the feed, listed from the antenna toward the chip (shunt first = shunt on the antenna side). Real parts on pads with a trace and Q 30-50 give less (BSN: -15.3 dB ideal became -10.9 dB).

![S11](s11.png)

## Efficiency (raw own far-field transform, about +-10 %)

| f (GHz) | radiation eff. | total eff. (no match) | Dmax (dBi) |
|---|---|---|---|
| 2.40 | 28 % | 7 % | 2.6 |
| 2.44 | 40 % | 17 % | 2.5 |
| 2.48 | 43 % | 38 % | 2.5 |

## Run

board `build/r4/board.json`, battery True, mask none, model m3, 2047890 cells, 4005 s.

# C23 rev B antenna recommendation

Status 2026-11-04 morning. Based on the openEMS runs in this folder (records in [DESIGNS.md](DESIGNS.md)).
Numbers are simulation results with ideal matching parts unless a line says otherwise.

## Antenna to order

IFA on the b2 layout (L4 removed, via fence and ground fill 1.4 mm lower, ground edge at KiCad y 90.4).
Footprint `IFA_2G4_B2` in `hardware/C23/library/BSN-C23.pretty`, made with

    python gen_ifa_footprint.py --sim '{"S":3.5,"Ws":2,"Wf":1,"H":5.0,"Wa":1,"L":9.0}' --name IFA_2G4_B2

Place it with its origin on AE1 (KiCad 144.1, 90.225). `IFA_2G4` is untouched.

| part | KiCad x | KiCad y | width |
|---|---|---|---|
| short leg | 139.6 .. 141.6 | 84.4 .. ground | 2 mm |
| feed leg (AE1) | 143.6 .. 144.6 | 85.4 .. notch | 1 mm |
| arm | 139.6 .. 159.0 | 84.4 .. 85.4 | 1 mm |

Arm 5 mm above the ground edge, 0.75 mm from the nearest board edge. Antenna copper stays under solder mask.

## Matching

The antenna is tuned so its own resonance sits above the band (2.59 GHz with the mask modelled).

### Parts on the real pads (3-port run, the numbers to use)

Run [ee6d48c654](runs/ee6d48c654) simulates J2, the L2 pad gap and the L3 pads as three ports with the explicit mask,
so the trace between J2 and the parts is included. `match.py` then fits E-series 0402 parts with loss
(inductor Q 35, capacitor ESR and ESL).

| L2 (series) | L3 (shunt) | worst BLE channel | resonance -1 % | resonance +1 % |
|---|---|---|---|---|
| 0R | open | -5.9 dB | | |
| 0R | 4.3 nH | -10.9 dB | | |
| 1.0 nH | 5.6 nH | -15.6 dB | -12.2 dB | -11.8 dB |
| 1.2 nH | 6.8 nH | -15.7 dB | -12.3 dB | -12.0 dB |
| 1.3 nH | 7.5 nH | -15.6 dB | -12.4 dB | -12.0 dB |

The +-1 % columns scale the frequency axis of the 3-port data (about +-26 MHz, the er +-5 % range). That is an
estimate, not a separate run. Re-picking the parts at either shift gets back to about -15.4 dB
(+1 %: L2 2.2 nH, L3 9.1 nH. -1 %: L2 22 pF, L3 4.3 nH).

So the one-inductor match seen with an ideal part at J2 (-15.3 dB with 3.5 nH, table below) does not survive the real
pad positions. With the parts where they are on the board, **two parts are needed: L2 about 1.2 nH and L3 about 6.8 nH.**
L2 cannot stay 0R.

### Best estimate (mask and finer mesh together)

Run [5393b94279](designs/5393b94279/summary.md) has the explicit mask and the finer mesh. It resonates at 2.598 GHz,
10 MHz (0.4 %) above the mask run on the normal mesh. Applying that shift to the 3-port data:

| L2 | L3 | best estimate | -1 % around it | +1 % around it |
|---|---|---|---|---|
| 1.2 nH | 6.8 nH | -14.0 dB | -15.7 dB | -10.8 dB |
| **1.5 nH** | **6.8 nH** | **-15.5 dB** | -13.8 dB / -12.0 dB at -0.6 % | -11.9 dB |
| 1.6 nH | 7.5 nH | -15.5 dB | -12.0 dB at -0.6 % | -11.9 dB |

(-1 % column for 1.2 / 6.8 is the normal-mesh mask run itself. For 1.5 / 6.8 the two numbers are -0.4 % and -1 %
from the best estimate.) So the best single guess for the first boards is **L2 1.5 nH, L3 6.8 nH**, and the tuning
kit below covers the +-1 % range.

### Definitive parts table (3-port with mask and finer mesh)

Run [5b8536e8e4](runs/5b8536e8e4) repeats the 3-port run with the explicit mask and the finer mesh. It confirms the
scaled estimate above.

| L2 | L3 | worst BLE channel | -1 % | +1 % |
|---|---|---|---|---|
| 0R | open | -5.5 dB | | |
| 0R | 4.7 nH | -9.4 dB | | |
| **1.6 nH** | **6.8 nH** | **-15.5 dB** | -12.0 dB | -11.7 dB |
| 1.5 nH | 6.8 nH | -15.0 dB | -12.5 dB | -11.4 dB |
| 1.8 nH | 8.2 nH | -15.5 dB | | |
| 1.2 nH | 6.8 nH | -13.2 dB | -14.2 dB | -10.3 dB |

**Parts for the order: L2 1.6 nH (1.5 nH is within 0.5 dB), L3 6.8 nH.**

### Ideal part at J2 (1-port runs, for the tolerance trend)

| case | resonance | worst BLE channel, no parts | 1 ideal part at J2 | 2 ideal parts |
|---|---|---|---|---|
| as built, 20 um mask modelled ([cae851224d](designs/cae851224d/summary.md)) | 2.588 GHz | -5.8 dB | -15.3 dB, 3.5 nH | -15.3 dB |
| no mask ([7d3b8b589d](designs/7d3b8b589d/summary.md)) | 2.607 GHz | -5.3 dB | -12.3 dB, 3.5 nH | -14.9 dB |
| no mask, finer mesh | 2.619 GHz | -5.0 dB | -10.0 dB, 3.75 nH | -15.2 dB |
| no mask, FR4 er -5 % | 2.634 GHz | -4.7 dB | -8.9 dB, 4.0 nH | -15.3 dB |
| no mask, FR4 er +5 % | 2.582 GHz | -6.0 dB | -14.3 dB, 4.5 nH | -14.3 dB |
| no mask, no battery | 2.602 GHz | -5.5 dB | -12.9 dB, 3.5 nH | -15.5 dB |

The resonance tolerance from the inputs I know is about +-30 MHz (er +-5 % gives +-26 MHz, the mesh about +12 MHz,
the battery about 5 MHz, the mask -19 MHz is already in the as-built row).

### For the bench

- Start with L2 = 1.6 nH and L3 = 6.8 nH. The definitive 3-port run says -15.5 dB in the whole band.
- Measure S11 at J2 with a VNA and re-pick both parts. Without a VNA the parts above are the best guess.
- Tuning kit (0402 RF inductors, for example Murata LQW15 or LQG15): L2 0R, 0.8, 1.0, 1.2, 1.5, 1.8, 2.2 nH and
  L3 3.9, 4.3, 4.7, 5.6, 6.8, 7.5, 8.2, 9.1 nH, plus a few 22 pF for L2.

## Efficiency and pattern

- Radiation efficiency 85 to 95 % in the band, from the own far-field transform after calibration. The transform is validated to about +-15 %, so this says "no large loss", not an exact number.
- Peak directivity about 2 dBi, near-omni pattern with two shallow nulls of about -7 dB. Plots in each design record.

## Would a bigger board help

Yes, a bigger ground is the strongest lever left. Same antenna (H5.0), arm length re-tuned:

| board | worst BLE channel, no parts | 1 part | 2 parts |
|---|---|---|---|
| 34 x 34 mm (this board) | -5.8 dB | -15.3 dB | -15.3 dB |
| 5 mm taller | -7.0 dB | -16.2 dB | -17.7 dB |
| 10 mm taller | -9.5 dB | -17.6 dB | -19.8 dB |
| 4 mm wider | -8.7 dB | -16.0 dB | -17.4 dB |
| 8 mm wider | -15.3 dB (L9.0 run) | -20.5 dB (L9.2 run, 9.5 nH) | -20.5 dB |

Making the board 8 mm wider (in the antenna direction) gives a match better than -10 dB with no parts at all.
For a beacon, -10 dB already loses only 0.5 dB, and -15 dB loses 0.14 dB. So the 34 x 34 mm board with two parts on L2 and L3 is
already close to what matching can give, and a bigger board mostly buys margin against tolerance.

Re-tuned arm lengths (size3 batch, ideal parts at J2):

| board | L | resonance | no parts | 1 part | 2 parts |
|---|---|---|---|---|---|
| 8 mm wider | 9.6 | 2.466 GHz | -16.1 dB | -19.8 dB | -20.1 dB |
| 8 mm wider | 9.2 | 2.516 GHz | -11.7 dB | -20.5 dB | -20.5 dB |
| 8 mm wider | 8.6 | 2.598 GHz | -8.1 dB | -14.4 dB | -20.7 dB |
| 8 mm wider, 10 mm taller | 9.2 | 2.552 GHz | -10.6 dB | -18.3 dB | -22.0 dB |
| 10 mm taller | 8.6 | 2.700 GHz | -5.4 dB | -8.8 dB | -19.2 dB |

On the 8 mm wider board, L 9.6 puts the resonance in the band and gives -16 dB with no parts at all, which also
removes most of the tolerance worry. Wider helps more than taller. Adding height on top of width gains only about
1 to 2 dB more. 3-port run of the 8 mm wider board, L 9.6, no mask ([9b0c89d717](runs/9b0c89d717)), real parts on the real pads:

| L2 | L3 | worst BLE channel |
|---|---|---|
| 0R | open | -16.6 dB |
| 3 pF | 7.5 nH | -19.5 dB |

With no parts it stays between -13.8 and -19.1 dB for a +-1 % resonance shift, so this board would work without
any tuning (the mask moves it about -0.75 %, toward the better end). The cost is 8 mm more board width.

## What was tried and did not help

- Wider arm, wider short leg, bent or folded end (FIFA): no wider band on this board.
- Arm height is the main lever, and H5.0 is the highest that fits under the top edge with the margin.

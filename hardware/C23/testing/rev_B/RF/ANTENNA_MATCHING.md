# BSN-C23-B antenna matching (printed IFA)

VNA measurements at J2 (Murata MM8130) on rev B, to tune L2 and L3 and to compare with the openEMS simulation in
[`../../RF/antenna_C23-B/README.md`](../../RF/antenna_C23-B/README.md). The rev A measurements (chip antenna) are
in [`../../rev_A/RF/ANTENNA_MATCHING.md`](../../rev_A/RF/ANTENNA_MATCHING.md).

## Result

- L2 1.6 nH and L3 6.8 nH, the values from the simulation, stay. No part was changed (decision 2026-11-13).
- With the coin cell fitted, the worst S11 in the BLE band on B #2 is −12.0 dB with the board hanging in the air
  and −18.8 dB with the board standing on its battery holder on the table.
- Lying flat on the table without the holder, the antenna is detuned by about 330 MHz and the band is not matched.

## Boards

| Board | 100 µF caps | J2 goes to | Matching parts |
|---|---|---|---|
| B #1 | none | antenna | L2 0 Ω, L3 open (antenna without parts) |
| B #2 | 1 | antenna | L2 1.6 nH series, L3 6.8 nH shunt (the simulated start values) |
| B #3 | 2 | PA | not fitted |

## Measurement setup (2026-11-13)

- Keysight P9370B (MY61100412), 1 port.
- Murata MM8130 probe plugged into J2. The probe disconnects the chip side, so the VNA sees L2, L3 and the antenna.
- Table: wood, covered with a rubber protective sheet of about 2 mm (not ESD).

Board conditions used in the file table:

| Name | Condition |
|---|---|
| on holder | On the table, the PCB resting on a loose battery holder (not soldered), which keeps it lifted about 5 mm off the surface. No coin cell |
| on holder, cell | On the table on the battery holder, now soldered, with a CR2032 in it |
| flat | On the table, battery holder side down, without the holder, so the PCB lies on the surface. No coin cell |
| in air | Hanging by the coax of the probe. No holder, no coin cell |
| in air, cell | Hanging by the coax of the probe, holder soldered, CR2032 in it |

The battery holder was left off until it was clear that the matching parts stay, because parts are easier to swap
without it. On rev A the lift off the table made the difference, not whether the holder was soldered. The holder
was soldered right before the first sweep with the cell (file 07, 16:24). Files 03 to 06 are without a soldered
holder, files 07 to 10 with it. So the comparison "cell against no cell" also contains the soldered holder.

### Final calibration (files 03 to 10)

- Span 1.0–4.0 GHz, 1601 points (1.875 MHz steps).
- Open, short and load all at the tip of the probe:
  - open: the probe with nothing connected
  - short: a mating MM8130 connector with a short
  - load: a mating MM8130 connector with two 100 Ω resistors in parallel
- Then 46 ps of port extension, so that open and short sit at the open and the short of the Smith chart. Likely
  needed because the calibration kit definition in the VNA gives its open and short a length that these
  home-made standards do not have (not checked which kit is selected).
- The first 50 Ω standard had the resistors on the wrong pins of the connector (in and out). That calibration gave
  |Γ| up to 2.97 on a passive antenna and was discarded, the files were not kept. Seeing the open and the short
  at the right places after a calibration is not a check, because they are the standards the calibration was
  made with.
- Left over: |Γ| is above 1 below 1.38 GHz in file 03 and below 1.81 GHz in file 04, by up to 0.07. Between 2.0
  and 3.0 GHz it stays below 0.94 in all files. Cause not investigated.
- With the board hanging by the coax, currents on the cable shield can be part of the reading. Not checked.

### First calibration (files 01 and 02, mixed planes, superseded)

- Span 2.0–3.0 GHz, 1601 points (0.625 MHz steps).
- Open and short at the tip of the probe, but the load at port 1 without the probe, then 45 ps of port extension.
- The reflection of the probe itself is not removed by this. The files are kept for the record and are not used.
- An attempt before that had the port extension set with one marker at 2.44 GHz and was one full turn short
  (about 0.43 ns round trip left over 2.0–3.0 GHz). Not kept.

## Measurements

All files are the VNA's CSV export (frequency, R, X in ohms). The −10 dB band is taken between 2 and 3 GHz.

B #2, L2 1.6 nH, L3 6.8 nH:

| File | Condition | S11 minimum | −10 dB band | Worst S11 in 2.400–2.4835 GHz | Z at 2.40 / 2.44 / 2.48 GHz (Ω) |
|---|---|---|---|---|---|
| `s11_04_B2_L2-1n6_L3-6n8.csv` | on holder | −42 dB at 2.420 GHz | 2309–2550 MHz (241) | −15.9 dB | 52.0 − j4.8 / 50.0 + j5.9 / 49.5 + j15.4 |
| `s11_07_B2_L2-1n6_L3-6n8_bat-fitted.csv` | on holder, cell | −39 dB at 2.440 GHz | 2328–2566 MHz (238) | −18.8 dB | 53.8 − j10.6 / 51.0 + j0.3 / 50.1 + j10.6 |
| `s11_05_B2_L2-1n6_L3-6n8_in-air.csv` | in air | −18.2 dB at 2.464 GHz | 2371–2558 MHz (187) | −12.5 dB | 44.1 − j22.2 / 40.8 − j10.0 / 38.4 + j1.1 |
| `s11_08_B2_L2-1n6_L3-6n8_in-air_bat-fitted.csv` | in air, cell | −18.3 dB at 2.479 GHz | 2375–2562 MHz (187) | −12.0 dB | 45.2 − j24.1 / 41.3 − j12.7 / 39.1 − j1.2 |
| `s11_06_B2_L2-1n6_L3-6n8_flat.csv` | flat | −15.7 dB at 2.112 GHz | 2031–2208 MHz (177) | −3.4 dB | 50.8 + j77.7 / 54.8 + j87.3 / 59.7 + j98.8 |

B #1, antenna without parts (L2 0 Ω, L3 open):

| File | Condition | S11 minimum | −10 dB band | Z at 2.40 / 2.44 / 2.48 GHz (Ω) |
|---|---|---|---|---|
| `s11_03_B1_antenna_unmatched.csv` | on holder | −35 dB at 2.538 GHz | 2396–2663 MHz (267) | 33.4 − j20.3 / 36.8 − j13.9 / 41.0 − j8.1 |
| `s11_09_B1_antenna_unmatched_bat-fitted.csv` | on holder, cell | −26.2 dB at 2.562 GHz | 2427–2682 MHz (255) | 31.5 − j24.8 / 33.6 − j18.6 / 36.7 − j12.0 |
| `s11_10_B1_antenna_unmatched_in-air_bat-fitted.csv` | in air, cell | −14.2 dB at 2.582 GHz | 2487–2672 MHz (185) | 23.7 − j26.3 / 25.3 − j19.7 / 27.7 − j13.1 |

Superseded (first calibration): `s11_01_B2_L2-1n6_L3-6n8_mixed-cal.csv` and
`s11_02_B1_antenna_unmatched_mixed-cal.csv`, both on holder.

What the conditions do:

- The table under the board moves the response down in frequency and widens the −10 dB band: by 37 to 59 MHz and
  about 50 MHz wider for the matched board (files 07 and 04 against 08 and 05), by 20 MHz and 70 MHz wider for the
  antenna without parts (file 09 against 10).
- The soldered holder with the coin cell changes little: the matched minimum moves up by about 15 to 20 MHz, on
  the holder and in the air.
- On the table the match happens to be centred in the band. In the air it sits about 35 MHz higher and is less
  deep, with the band still below −12 dB.

## Simulation against measurement

The simulation has the board in free space with the CR2032 as a metal disc 0.5 mm under B.Cu. The matching
measured case is "in air, cell": file 10 for the antenna without parts and file 08 for the matched board.
Simulated curves: `antenna_C23-B/data/s11_no_parts.csv` (1-port run), `s11_matched_cascade.csv` (3-port run with
part models) and `s11_matched_fdtd.csv` (full-wave run with the parts, no solder mask).

Antenna without parts, B #1, file 10:

| Quantity | Simulated | Measured | Difference |
|---|---|---|---|
| S11 minimum | −15.8 dB at 2.594 GHz | −14.2 dB at 2.582 GHz | −12 MHz, −0.5 % |
| −10 dB band | 2495–2707 MHz (212 MHz) | 2487–2672 MHz (185 MHz) | 27 MHz narrower |
| Z at 2.40 GHz | 26.9 − j39.5 Ω | 23.7 − j26.3 Ω | R −3.2, X +13.2 |
| Z at 2.44 GHz | 28.1 − j29.7 Ω | 25.3 − j19.7 Ω | R −2.8, X +10.0 |
| Z at 2.48 GHz | 29.7 − j20.3 Ω | 27.7 − j13.1 Ω | R −2.0, X +7.2 |

With L2 1.6 nH and L3 6.8 nH, B #2, file 08:

| Quantity | Simulated, cascade | Simulated, full wave | Measured | Difference to the cascade |
|---|---|---|---|---|
| S11 minimum | −52.7 dB at 2.442 GHz | −49.7 dB at 2.455 GHz | −18.3 dB at 2.479 GHz | +37 MHz, +1.5 % |
| −10 dB band | 2368–2528 MHz (160 MHz) | 2376–2545 MHz (169 MHz) | 2375–2562 MHz (187 MHz) | 27 MHz wider |
| Worst S11 in the BLE band | −14.9 dB | −13.1 dB | −12.0 dB | 2.9 dB worse |
| Z at 2.40 GHz | 62.5 − j16.2 Ω | 65.7 − j20.5 Ω | 45.2 − j24.1 Ω | |
| Z at 2.44 GHz | 50.4 − j0.9 Ω | 53.1 − j5.3 Ω | 41.3 − j12.7 Ω | |
| Z at 2.48 GHz | 42.9 + j12.1 Ω | 45.2 + j7.9 Ω | 39.1 − j1.2 Ω | |

Whole-curve comparison over 2.3–2.6 GHz, as the distance between the simulated and the measured reflection
coefficient (rms of |ΔΓ|), and the frequency shift of the simulated curve that makes it smallest:

| Pair | rms \|ΔΓ\| as simulated | Best-fit shift of the simulation | rms \|ΔΓ\| after the shift |
|---|---|---|---|
| No parts (file 10) | 0.18 | −1.7 % | 0.10 |
| Matched, cascade (file 08) | 0.20 | 0.0 % | 0.20 |
| Matched, full wave (file 08) | 0.19 | −0.4 % | 0.19 |

Notes:

- Antenna without parts: the S11 minimum is 0.5 % below the simulated one, inside the ±2 % the simulation
  write-up expected. The resistance agrees within about 3 Ω, the reactance is 7 to 13 Ω less capacitive than
  simulated.
- Matched: the minimum is 1.5 % above the simulated one, inside ±2 %. It is less deep than simulated, the real
  part at 2.44 GHz is 41 Ω against 50 Ω. The band is below −12.0 dB against −14.9 dB simulated.
- The antenna without parts is lower in frequency than simulated and the matched board is higher. These are two
  boards, and the matched board adds the tolerance of L2 and L3 and their pads. Not investigated further.
- On the holder on the table (files 04, 07, 03, 09) the bands are 50 to 70 MHz wider than in the air. The wider
  bands in those files come with the table, so they say nothing about loss in the antenna itself.
- Causes of the differences are not investigated. Candidates: FR4 εr, prepreg and core thickness, copper width
  after etching, solder mask, the model itself, the reference plane (the simulation port is at J2 pad 1, the
  measurement plane is the tip of the probe, with the mated connector in between), the 0 Ω part on L2, the real
  cell and holder against a plain metal disc, and the coax the board hangs on.
- The depth of a minimum below about −30 dB depends on the last few hundredths of Γ and is not a number to compare.

## To do

- [ ] Save an independent check of the calibration as a file (a standard that was not used for it).
- [ ] Hand L-match on the Smith chart from the measured impedance without parts. Calculated, simulated and final
      values side by side. Planned for the weekend of 14–15 Nov.
- [ ] Fit L2 1.6 nH and L3 6.8 nH on B #1 and B #3.

# BSN-C23-B spectrum analyser (carrier frequency, conducted power, harmonics)

Measurements on B #3 with the `cwtest` firmware, at the uni on 2026-11-17. One session, the analyser was lent
on the spot by Kasper and could not come back. The rev A chip-antenna measurements are in
[`../../rev_A/RF/RF_CARRIER.md`](../../rev_A/RF/RF_CARRIER.md).

## Result

- **Carrier frequency within about +/-0.7 ppm** of the analyser reference on all three channels. The absolute
  bound is set by the analyser reference accuracy, which is not yet known (see open items). No sign of a large
  fixed offset. The +120 kHz / +49 ppm read earlier at 2440 MHz was an artefact of a 1 MHz RBW and is
  discarded.
- **Conducted power at J2: +2.4 dBm at the +8 dBm setting, -4.7 dBm at the 0 dBm setting** (2440 MHz, read at
  the analyser, probe and cable loss not corrected). The step between the two settings is 7.1 dB.
- **H5 (12.0 to 12.4 GHz) is about -41 dBm and sits on the FCC restricted-band line of -41.2 dBm**, before any
  probe and cable loss is added back. It is a real signal from the board, confirmed by an attenuation check and
  a board-off check. This is conducted, not radiated (EIRP), so whether the node passes radiated is open and is
  for the chamber. H2 to H4 are all below about -54 dBm.
- H5 is about 10 dB worse than on rev A relative to the carrier (-40.9 dBm against -50.7 dBm at +8 dBm,
  2440 MHz), although the pi network is the same parts. The RF path differs: J2 (MM8130) sits between the pi
  network and the antenna, the routing bends, there is no U.FL stub, and the vias are placed differently. Which
  of these dominates is not investigated. Placed in the Discussion, H5 added to the chamber list.

## Board and setup

- B #3: two 100 uF bulk caps, J2 to the PA, L2 1.6 nH and L3 6.8 nH fitted, pi network (C8, L1, C9) unchanged
  from rev A. `cwtest` firmware (`firmware/C23/cwtest`), HFXT trim 44.
- Measurement point: the Murata MXHS83QE3000 probe on J2, plus the analyser cable. **The insertion loss of the
  probe and cable is not measured**, so all levels are as read. Both the probe and the cable are only specified
  to 6 GHz, so the H2 to H5 readings carry an unknown connector loss.
- Supply: AA cells at about 3.2 V into the board (the node runs from the DC-DC, so the exact supply has little
  effect). The user to confirm the voltage during the readings.
- Analyser: Rohde & Schwarz Spectrum Rider FPH, model .26, firmware V2.11. Its clock is wrong (dates read 2021
  and 2022), so the CSV timestamps are not the measurement date.

## Carrier frequency and power (2440 MHz, RBW 1 kHz, span 100 kHz, ATT 20 dB, Average 10, Sample detector)

| Channel | File | Peak | Offset | ppm | Level |
|---|---|---|---|---|---|
| 2402 MHz | `sa_01` | 2402.00056 MHz | +0.56 kHz | +0.23 | +3.2 dBm |
| 2402 MHz (repeat) | `sa_19` | 2401.99845 MHz | -1.55 kHz | -0.65 | +3.2 dBm |
| 2440 MHz | `sa_02` | 2439.99887 MHz | -1.13 kHz | -0.46 | +2.4 dBm |
| 2480 MHz | `sa_03` | 2480.00169 MHz | +1.69 kHz | +0.68 | +2.1 dBm |
| 2440 MHz, 0 dBm | `sa_24` | 2440.00169 MHz | +1.69 kHz | +0.69 | -4.7 dBm |

`sa_20` is the 2480 MHz carrier taken with the Max Peak detector instead of Sample (+2.16 dBm, same frequency),
kept as a detector cross-check. The two 2402 runs differ by 2.1 kHz (about 0.9 ppm), which gives a feel for the
run-to-run spread, cause not investigated (likely the board warming after each power cycle).

The 2402 and 2480 carriers show sidebands at about +/-30 kHz, roughly -40 dBc. They are not present at
2440 MHz. Cause not investigated.

## Conducted power step

| Setting | File | Level at 2440 MHz |
|---|---|---|
| +8 dBm | `sa_02` | +2.4 dBm |
| 0 dBm | `sa_24` | -4.7 dBm |

Step 7.1 dB for an 8 dB change in setting. The probe and cable loss cancels in the step. Rev A read +5.2 dBm at
+8 dBm and -3.2 dBm at 0 dBm through a U.FL pigtail, a step of 8.4 dB. The rev B levels are lower because of the
MM8130 probe loss, not corrected here.

## Harmonics (span 1 MHz, RBW 10 kHz, ATT 20 dB, Max Hold, Max Peak)

Levels at the exact n x carrier. "< floor" where no peak rises above the noise, the value is then the floor.
Red line in the plot is -41.2 dBm, the FCC restricted-band limit (EIRP), used here only as a stand-in for the
conducted reading.

| Carrier | H1 | H2 | H3 | H4 | H5 | Files |
|---|---|---|---|---|---|---|
| 2402 MHz | +3.3 | -54.3 | -61.2 | < -66 | **-41.1** | `sa_04`-`sa_08` |
| 2440 MHz | +2.4 | -60.8 | -66.7 | -65.0 | **-40.9** | `sa_09`-`sa_13` |
| 2480 MHz | +2.2 | -65.9 | -65.0 | < -66 | **-41.9** | `sa_14`-`sa_18` |

All in dBm, as read. The H4 markers at 2402 and 2480 MHz landed on noise 200 to 370 kHz off the harmonic, so
H4 is not detected on those two channels. The floor is about -69 dBm, higher than the -80 dBm it would be at
ATT 10 dB with the preamp on. It is still low enough for the "not detected" upper bounds. H5 is the only
harmonic near a limit, and it is near it on every channel.

### H5 is real and from the board

| File | Setting | Level at 12200 MHz |
|---|---|---|
| `sa_13` | ATT 20 dB, board on | -40.9 dBm (floor about -67) |
| `sa_21` | ATT 30 dB, board on | -40.3 dBm (floor about -59) |
| `sa_22` | ATT 20 dB, board off | nothing, -71 dBm (floor about -70) |

Adding 10 dB of attenuation raised the floor by 10 dB but left H5 within 0.6 dB, which is how a real input
signal behaves (the display is corrected for the attenuator, a signal made inside the analyser would move).
With the board off there is nothing at 12200 MHz. So H5 is a real signal present at J2, coming from the board.

## Band edge (2480 MHz carrier, span 10 MHz, RBW 100 kHz, ATT 20 dB, Max Hold)

File `sa_23`. CW carrier at 2480 MHz, +8 dBm.

| Frequency | Level |
|---|---|
| Carrier, 2480.01 MHz | +2.3 dBm |
| 2482 MHz | -50.5 dBm |
| 2483.5 MHz (band edge) | -56.4 dBm, about 59 dB below the carrier |
| Peak above 2483.5 MHz | -55.3 dBm at 2483.7 MHz |
| Floor, 2486 to 2488 MHz | about -60.5 dBm |

At the edge of the band the CW skirt is already about 4 dB above the floor and about 15 dB under -41.2 dBm.
This is for an unmodulated carrier. The advertising spectrum, which is modulated and wider, is a separate
measurement and is not covered here.

## CW supply current

Measured the same day at the power lab, B #3 at 2440 MHz on a 3.0 V PSU: 6.14 mA at 0 dBm, 10.90 mA at +4 dBm,
14.20 mA at +8 dBm. Used for the chamber battery budget, full note in
[`../Power/CW_CURRENT.md`](../Power/CW_CURRENT.md).

## File list

All files are R&S FPH CSV exports, numbered in the order measured. `sa_01` to `sa_03` are the three channels at
the final carrier settings, `sa_04` to `sa_18` the harmonics H1 to H5 for 2402 / 2440 / 2480 MHz, `sa_19` the
2402 repeat, `sa_20` the 2480 Max Peak cross-check, `sa_21`/`sa_22` the H5 checks, `sa_23` the band edge,
`sa_24` the 0 dBm carrier. Plots: [`plots_2026-11-17/6_carriers.png`](plots_2026-11-17/6_carriers.png) and
[`7_harmonics.png`](plots_2026-11-17/7_harmonics.png), from `plots_2026-11-17/spectrum.py`.

## Open items

- Analyser reference accuracy (R&S FPH .26). Without it the carrier offset can only be stated as "within the
  reference accuracy". Ask Kasper whether an external 10 MHz reference was fitted. Not investigated.
- **Insertion loss of the MXHS83QE3000 probe and the analyser cable. Needed before any level in this file is a
  true conducted power.** The Murata documents found give no loss figure (searched 2026-11-18). Method on the
  VNA: one-port calibration at the VNA end, then the probe and the analyser cable connected as on 2026-11-17,
  with the probe on the short standard of 2026-11-13. The reading is the round-trip loss, half of it in dB is
  the one-way loss. The open and the 50 Ω standard as checks. The P9370B reaches 4.5 GHz, so this corrects the
  carrier but not H2 to H5. Without it, the conducted power at J2, the link budget and the efficiency from a
  TRP measurement all carry an unknown offset.
- H5 radiated level (EIRP) in the chamber, which is what the FCC limit is written against. The conducted -41 dBm
  is only a stand-in. Add H3 as well.
- Why H5 is about 10 dB worse than rev A: pi network parasitics, the MM8130 and its pads, or the changed
  routing and vias. Not investigated, goes in the Discussion.
- The +/-30 kHz sidebands at 2402 and 2480 but not 2440. Not investigated.

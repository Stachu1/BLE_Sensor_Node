# Radiated measurements in the antenna chamber (2026-11-19)

3D radiation pattern, total radiated power (TRP) and peak EIRP of BSN-C23-B and BSN-C23-A, plus the 2nd to 5th
harmonic, measured in the antenna chamber at SDU with the lab's automated antenna measurement software. The
results are calibrated by the lab for the chamber (receive antenna, cables and receiver), so the levels in the
reports are EIRP and TRP directly.

## Setup

- Each board ran `cwtest` (unmodulated carrier, 2440 MHz, 0 dBm setting) on its own CR2032 in the on-board
  holder. No cable to the board.
- Board taped to the positioner. One point every 20° in azimuth and elevation, both polarisations, combined by
  the software. RBW 1 MHz.
- Receiver R&S ESR-26, receive antenna R&S HF907 (transducer `HF907.tdf`).
- Rev B was flashed from `main`, rev A from the tag `fw/BSN-C23-A` (rev A pin set).

## Files

Renamed from the names the lab software gave them. The software labelled every rev B report "BSN-C23-B_2",
including the B #9 run, so the board is taken from the run times. Numbered in the order they were taken.

| File | Board | Run | Measured at | Use |
|---|---|---|---|---|
| `chamber_2026-11-19/ch_01_B2_2400-7200-12000MHz_wrong-freq.pdf` | B #2, pi network fitted | 11:57-12:25 | 2400 / 7200 / 12000 MHz | None, 40 MHz off the carrier |
| `chamber_2026-11-19/ch_02_B2_4800MHz_wrong-freq.pdf`, `ch_03_B2_9600MHz_wrong-freq.pdf` | B #2 | same run | 4800 / 9600 MHz | None |
| [`../../rev_A/RF/chamber_2026-11-19/ch_01_A1_2440-7320-12200MHz.pdf`](../../rev_A/RF/chamber_2026-11-19/) | A #1 | 13:00-13:24 | 2440 / 7320 / 12200 MHz | Rev A result |
| `../../rev_A/RF/chamber_2026-11-19/ch_02_A1_4880MHz.pdf`, `ch_03_A1_9760MHz.pdf` | A #1 | same run | 4880 / 9760 MHz | Rev A harmonics |
| `chamber_2026-11-19/ch_04_B2_no-pi_2400-7200-12000MHz_wrong-freq.pdf` | B #2, pi network removed | 13:39-14:03 | 2400 / 7200 / 12000 MHz | None, 40 MHz off the carrier |
| `chamber_2026-11-19/sweep_01_B9_cw2440_0dBm_2-13GHz_rbw10k` (`.DAT`, `.csv`) | B #9 | 14:23 | 2-13 GHz, RBW 10 kHz | Harmonic search |
| `chamber_2026-11-19/sweep_02_B9_cw2440_0dBm_2-13GHz_rbw1k` (`.DAT`, `.csv`) | B #9 | 14:25 | 2-13 GHz, RBW 1 kHz | Harmonic search |
| `chamber_2026-11-19/ch_05_B9_2440-7320-12200MHz.pdf` | B #9, pi network fitted | 14:13-14:37 | 2440 / 7320 / 12200 MHz | Rev B result |
| `chamber_2026-11-19/ch_06_B9_4880MHz.pdf`, `ch_07_B9_9760MHz.pdf` | B #9 | same run | 4880 / 9760 MHz | Rev B harmonics |

The `.DAT` files are the receiver's own export. The `.csv` files hold the same points in the layout of the VNA
files (`!` header lines with the settings, then `Freq(Hz),Level(dBuV/m)`).

The first B #2 run was set up at 2400 MHz while the board transmitted at 2440 MHz. Its harmonic results led to
removing the pi network from B #2, and it was measured again, still at 2400 MHz. The error was then found and B #9 (as
built, with the pi network) was measured at 2440 MHz. The two B #2 runs show only the noise floor (TRP about
-31.8 dBm at 2400 MHz, flat over all directions) and give no result for the pi network.

## Results at 2440 MHz

| Board | TRP | Peak EIRP | Directivity | Min. EIRP |
|---|---|---|---|---|
| B #9 (printed IFA) | **-0.74 dBm** | **+1.54 dBm** | 2.27 dBi | -5.04 dBm |
| A #1 (chip antenna) | **-4.52 dBm** | **-0.23 dBm** | 4.28 dBi | -12.08 dBm |

- Rev B radiates 3.8 dB more in total than rev A at the same 0 dBm setting, and its pattern is more even (6.6 dB
  between the strongest and the weakest direction, against 11.9 dB for rev A).
- The "Total Efficiency" in the reports is the TRP relative to an assumed 0 dBm input (84 % for B #9, 35 % for
  A #1). It is not the antenna efficiency, because the power delivered to the antenna was not 0 dBm.
- The TRP of B #9 (-0.74 dBm) is higher than the conducted power measured at J2 on B #3 on 2026-11-17 (-3.9 dBm
  at the 0 dBm setting, corrected for the probe loss, see [`SPECTRUM.md`](SPECTRUM.md)). A TRP above the
  conducted power is not physically possible for the same board and supply, so at least one of the two values is
  off, or the boards differ. Not investigated. Different boards (B #3 and B #9), the switch in J2 and the probe,
  and the chamber calibration are the candidates.

## Harmonics

- In the 3D runs every harmonic reads the same in all directions (within about 0.3 dB, directivity about
  0.15 dBi). That is the noise floor of the setup, not a signal. The floor in TRP terms is about -21 dBm at
  4880 MHz, -19.4 dBm at 7320 MHz, -13.7 dBm at 9760 MHz and -12.2 dBm at 12200 MHz, the same for A #1 and B #9.
  This floor is above the emission limits, so the 3D runs alone cannot show a margin to them.
- The two 2-13 GHz sweeps on B #9 (max hold, max-peak detector) have a lower floor. The carrier reads
  91.7 dBuV/m (1 kHz RBW). At 4880 / 7320 / 9760 / 12200 MHz no point rises more than 1.5 dB above the local
  noise (44.3 / 44.4 / 46.9 / 48.3 dBuV/m). No harmonic is detected, and each is at least about 42 dB below the
  carrier in the direction of the sweep.
- Converting the sweeps to EIRP needs the measurement distance, which is not in the files. Which direction the
  board faced during the sweeps is not recorded.

## Open

- [ ] Measurement distance and board direction for the two sweeps (ask the lab), to turn the sweep floor into an
      EIRP limit for H2 to H5.
- [ ] Why the B #9 TRP is above the conducted power at J2 on B #3.
- [ ] Compare the B #9 pattern with the simulated pattern (`../../RF/antenna_C23-B/data/pattern_2440MHz_matched.csv`).
- [ ] Pi network effect on the radiated harmonics: not measured (both B #2 runs at the wrong frequency).

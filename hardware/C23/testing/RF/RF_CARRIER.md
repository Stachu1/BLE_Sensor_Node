# BSN-C23-A carrier frequency and output power (2026-10-26)

Checking the HFXT frequency offset and the TX output power with the `cwtest` firmware
(`firmware/C23/cwtest`, unmodulated carrier at 2440 MHz), measured with the Keysight P9370B VNA used as a
receiver.

**Result:** with the factory HFXT cap trim (Q1 = Q2 = 35) the carrier was **+30.3 ppm** high, outside the
±20 ppm target. **`hfxtCapArrayQ1/Q2 = 44`** (set in `cwtest.syscfg` and `ble_sensor.syscfg`) brings it to
**+2.2 ppm**. Output power at the U.FL is 1.3–3.1 dB below the PA setting, about +6.7 dBm at the +8 dBm setting.

## Test board

A board with only the MCU, the 48 MHz crystal (X1), the pi network on the MCU side (C7, L1, C8) and J1 (U.FL)
fitted, and no antenna. J1 goes straight to VNA port 1. Flashed with `make jflash` (J-Link), followed by a
power cycle.

## VNA setup

Using a VNA as a receiver: the receiver is swept over the frequency span with the board's carrier as the
only signal.

- Trace: receiver **A** (port 1) with **source port 2** (`A,2`), Log Mag in dBm. Port 2 open, RF power off.
  With source port 1 (`A,1`) the VNA's own signal reflects off the board and swamps the carrier, and it
  drives the CC2340 RF pin.
- Span 1–10 MHz around 2440 MHz. The IF bandwidth was wide (the peak is about 90 kHz wide at −3 dB), so the
  carrier frequency is taken as the centre of the peak's −6 dB width rather than the highest point.
- **Thru offset:** port 2 sending 0 dBm at 2440 MHz into port 1 through the same cable reads −0.67 dBm on
  `A,2`. All levels below are corrected by +0.67 dB. The VNA's source level is itself only accurate to
  about ±1 dB.
- **Image response:** a wide sweep (file 01) shows a second peak of the same level 26 MHz below the carrier,
  at 2414 MHz. The VNA receiver has no image filter, so this is the image of the 2440 MHz carrier, not a
  second signal from the board. The spectrum analyser confirmed it (nothing at 2414 MHz, see
  [Harmonics](#harmonics-spectrum-analyser-2026-10-28)).

## Measurements

| File | HFXT trim (Q1 = Q2) | PA setting | Span / step | Level read | Level corrected | Carrier offset |
|---|---|---|---|---|---|---|
| [`cw_01_2440MHz_0dBm_100MHz-span_cap35.csv`](cw_01_2440MHz_0dBm_100MHz-span_cap35.csv) | 35 (factory) | 0 dBm | 100 MHz / 500 kHz | −2.85 dBm | −2.2 dBm | (too coarse), image at 2414 MHz |
| [`cw_02_2440MHz_0dBm_10MHz-span_cap35.csv`](cw_02_2440MHz_0dBm_10MHz-span_cap35.csv) | 35 | 0 dBm | 10 MHz / 500 Hz | −2.72 dBm | −2.1 dBm | +74.0 kHz (+30.3 ppm) |
| [`cw_03_2440MHz_4dBm_10MHz-span_cap35.csv`](cw_03_2440MHz_4dBm_10MHz-span_cap35.csv) | 35 | +4 dBm | 10 MHz / 500 Hz | +0.27 dBm | +0.9 dBm | +73.8 kHz (+30.2 ppm) |
| [`cw_04_2440MHz_8dBm_10MHz-span_cap35.csv`](cw_04_2440MHz_8dBm_10MHz-span_cap35.csv) | 35 | +8 dBm | 10 MHz / 500 Hz | +6.03 dBm | +6.7 dBm | +74.0 kHz (+30.3 ppm) |
| [`cw_05_2440MHz_0dBm_1MHz-span_cap39.csv`](cw_05_2440MHz_0dBm_1MHz-span_cap39.csv) | 39 | 0 dBm | 1 MHz / 312 Hz | −2.67 dBm | −2.0 dBm | +41.1 kHz (+16.8 ppm) |
| [`cw_06_2440MHz_0dBm_1MHz-span_cap44.csv`](cw_06_2440MHz_0dBm_1MHz-span_cap44.csv) | **44** | 0 dBm | 1 MHz / 312 Hz | −2.68 dBm | −2.0 dBm | **+5.3 kHz (+2.2 ppm)** |

The VNA marker on the peak maximum of file 06 read +6.25 kHz (+2.6 ppm). The centre of the peak is the
better estimate.

## What was learned

1. **Frequency offset:** the factory trim (35) puts this board +30 ppm high: inside the BLE limit of
   ±50 ppm, but outside the ±20 ppm target. The offset is the same at every PA setting, as expected for a
   crystal offset.
2. **Trim sensitivity:** about −3.4 ppm (−8 kHz) per step between 35 and 39, and −2.9 ppm (−7 kHz) per step
   between 39 and 44. Each step pulls a little less as the capacitance rises. Higher values lower the frequency.
3. **Why not 45:** one more step would give about −0.3 ppm, a smaller change than the VNA reference accuracy
   (a few ppm), crystal drift over temperature (around ±10 ppm) and the spread between boards. 44 stays.
4. **Output power:** relative to the PA setting, the corrected output is −2.1 dB at 0 dBm, −3.1 dB at +4 dBm
   and −1.3 dB at +8 dBm. A passive loss (pi network, cable) would be the same at every setting, so most of
   the shortfall is the PA itself at each setting, or the PA reacting to a load slightly different from TI's
   reference. The steps are +3.0 dB (0 → +4) and +5.8 dB (+4 → +8) instead of 4 dB each.

## Harmonics (spectrum analyser, 2026-10-28)

Both CW boards (with and without the pi network) on the uni's R&S Spectrum Rider FPH (model 26, firmware
2.11), conducted at J1 through an SMA to U.FL pigtail of about 15 cm plus adapters. Flashed with `make jflash`,
then J-Link unplugged and power-cycled. The CSV dates (11/11/2022) come from the analyser's clock.

**Result:** **the pi network is needed, and with it the board passes** at the +8 dBm setting at 2440 and 2480 MHz,
with at least 9.5 dB of margin. Without it, H3 fails the FCC limit at 0 dBm (by 0.6 dB) and H2 and H3 fail it
at +8 dBm (by 8 and 13 dB).

**Settings:** each harmonic on its own 3 MHz span, RBW = VBW 30 kHz, Auto Peak detector, RF attenuation 30 dB,
preamp off, reference level +10 dBm. In a wide span the trace points are 15–20 MHz apart and with a sample or
RMS detector the carrier read about 4.5 dB low, which is why each harmonic got its own span.

**Reading the files:** the saved marker comes from peak search. Where no harmonic rises above the noise, it
lands on a noise spike up to 1.5 MHz away. The levels below are the trace maximum within ±60 kHz of n × the
measured carrier frequency instead. "< x" means nothing above the noise floor there.

**Limits used:** −41.2 dBm for harmonics in FCC restricted bands (H2 4.5–5.15 GHz, H3 7.25–7.75 GHz,
H5 10.6–12.7 GHz), −30 dBm ETSI spurious for the rest. The FCC limit is for radiated power (EIRP), so the
conducted levels are only a stand-in for it.

All levels in dBm, as read (no cable correction):

| Board, setting, carrier | H1 | H2 | H3 | H4 | H5 | Files |
|---|---|---|---|---|---|---|
| pi network, 0 dBm, 2440 MHz | −3.2 | < −57 | < −59 | < −57 | < −57 | `harm_01`–`harm_05` |
| no pi, 0 dBm, 2440 MHz | −1.7 | −46.0 | **−40.6** ✗ | −45.7 | −54.4 | `harm_11`–`harm_15` |
| pi network, +8 dBm, 2440 MHz | +5.2 | < −56 | −55.7 | < −58 | **−50.7** | `harm_21`–`harm_25` |
| no pi, +8 dBm, 2440 MHz | +5.4 | **−33.1** ✗ | **−28.6** ✗ | −39.4 | −45.9 | `harm_31`–`harm_35` |
| pi network, +8 dBm, 2480 MHz | +4.5 | < −55 | < −58 | < −54 | −52.3 | `harm_41`–`harm_45` |

**Wide sweep** ([`sweep_01_nopi_8dBm_10MHz-15GHz.png`](sweep_01_nopi_8dBm_10MHz-15GHz.png) and `.csv`): the no-pi
board at +8 dBm, 10 MHz–15 GHz, RBW 100 kHz, 20 dB attenuation. The only peaks are the carrier and H2–H5, at
the same levels as the narrow-span files (within 0.6 dB). No other spurs and no 6th harmonic above the
floor of about −58 dBm. The point covering 2414 MHz reads −60.8 dBm, so **the 2414 MHz peak seen on the VNA was
the VNA's own image response**, not a signal from the board. The delta markers D2–D5 on the screenshot are
not on the harmonics, so ignore their values.

**Cable loss (estimate, not measured):** 1.13/1.37 mm micro-coax plus the U.FL, SMA and N adapters, about
0.5 dB at 2.4 GHz, 1 dB at 7.3 GHz and 1–2 dB at 12.2 GHz (U.FL is only rated to 6 GHz). The FPH read the N54
0.7 dB below the cable-corrected VNA, which fits. Corrected, the tightest margin (H5, pi network, +8 dBm, 2440 MHz)
drops from 9.5 to about 7.5–8.5 dB.

What was learned:

1. **The filter is required.** Without the pi network the board fails the FCC restricted-band limit at both
   power settings, mainly on H3, and only just passes ETSI at +8 dBm (H3 −28.6 against −30).
2. **The pi network removes 23 dB or more of H2, 27 dB of H3 and 19 dB or more of H4, but only about 5 dB of
   H5** (−45.9 → −50.7 dBm at +8 dBm). The 0402 parts probably have their own resonances near 12 GHz. H5 is the
   tightest margin with the network fitted. For the rev C filter, look at capacitors with a higher
   self-resonant frequency or a notch near 12 GHz.
3. **The pi network costs 0.2 dB at +8 dBm** (+5.4 → +5.2 dBm) but about 1.5 dB at 0 dBm (−1.7 → −3.2 dBm),
   so it changes the PA's load as well as filtering. At the power that will be used, its loss is negligible.
4. **The band edge is not worse:** at 2480 MHz H3 drops into the noise and H5 is 1.6 dB lower than at 2440 MHz.
   The carrier is 0.7 dB lower.
5. **Output power** agrees with the VNA: FPH −3.2 dBm against VNA −2.7 dBm read (0 dBm setting), +5.2 against
   +6.0 dBm read (+8 dBm setting).
6. **Conducted is not radiated.** On rev B the trace antenna may radiate the harmonics more or less efficiently
   than 2.44 GHz, probably by several dB either way.

## Open items

- [x] **2026-10-27:** instead of reworking this board, a second CW board was built without the pi network
      ("RF CW no-pi" in [`../../README.md`](../../README.md): C7/C8 off, L1 shorted, 15 pF DC block kept). This board
      re-measured on 2026-10-27: +9 kHz, −2.5 dBm at 0 dBm, consistent with the table above.
- [x] **2026-10-28 (uni, spectrum analyser):** output power, the 2414 MHz image and harmonics of both CW boards,
      with and without the pi network. See [Harmonics](#harmonics-spectrum-analyser-2026-10-28).
- [ ] Measure the offset with trim 44 on a second board, to separate a design offset from crystal spread.
- [x] Harmonics and spurious emissions (2nd–5th harmonic at 4.88–12.2 GHz) on the spectrum analyser.
- [ ] Rev B/C: keep the pi network and check its H5 (12.2–12.4 GHz) rejection when it is redesigned.
- [ ] Rev C: radiated pre-scan of H3 and H5 with the trace antenna.

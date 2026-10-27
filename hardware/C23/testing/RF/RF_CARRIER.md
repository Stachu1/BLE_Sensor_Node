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
  second signal from the board. Confirm on a spectrum analyser.

## Measurements

| File | HFXT trim (Q1 = Q2) | PA setting | Span / step | Level read | Level corrected | Carrier offset |
|---|---|---|---|---|---|---|
| [`cw_01_2440MHz_0dBm_100MHz-span_cap35.csv`](cw_01_2440MHz_0dBm_100MHz-span_cap35.csv) | 35 (factory) | 0 dBm | 100 MHz / 500 kHz | −2.85 dBm | −2.2 dBm | (too coarse), image at 2414 MHz |
| [`cw_02_2440MHz_0dBm_10MHz-span_cap35.csv`](cw_02_2440MHz_0dBm_10MHz-span_cap35.csv) | 35 | 0 dBm | 10 MHz / 500 Hz | −2.72 dBm | −2.1 dBm | +74.0 kHz (+30.3 ppm) |
| [`cw_03_2440MHz_4dBm_10MHz-span_cap35.csv`](cw_03_2440MHz_4dBm_10MHz-span_cap35.csv) | 35 | +4 dBm | 10 MHz / 500 Hz | +0.27 dBm | +0.9 dBm | +73.8 kHz (+30.2 ppm) |
| [`cw_04_2440MHz_8dBm_10MHz-span_cap35.csv`](cw_04_2440MHz_8dBm_10MHz-span_cap35.csv) | 35 | +8 dBm | 10 MHz / 500 Hz | +6.03 dBm | +6.7 dBm | +74.0 kHz (+30.3 ppm) |
| [`cw_05_2440MHz_0dBm_1MHz-span_cap39.csv`](cw_05_2440MHz_0dBm_1MHz-span_cap39.csv) | 39 | 0 dBm | 1 MHz / 312 Hz | −2.67 dBm | −2.0 dBm | +41.1 kHz (+16.8 ppm) |
| [`cw_06_2440MHz_0dBm_1MHz-span_cap44.csv`](cw_06_2440MHz_0dBm_1MHz-span_cap44.csv) | **44** | 0 dBm | 1 MHz / 312 Hz | −2.68 dBm | −2.0 dBm | **+5.3 kHz (+2.2 ppm)** |

The VNA marker on the peak maximum of file 06 read +6.25 kHz (+2.6 ppm); the centre of the peak is the
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

## Open items

- [x] **2026-10-27:** instead of reworking this board, a second CW board was built without the pi network
      ("RF CW no-pi" in [`../../README.md`](../../README.md): C7/C8 off, L1 shorted, 15 pF DC block kept). This board
      re-measured on 2026-10-27: +9 kHz, −2.5 dBm at 0 dBm, consistent with the table above.
- [ ] **Wednesday 2026-10-28 (uni, 28 GHz spectrum analyser):** output power, frequency offset (including the
      2414 MHz image) and harmonics of both CW boards, with and without the pi network. No rework at the uni.
- [ ] Measure the offset with trim 44 on a second board, to separate a design offset from crystal spread.
- [ ] Harmonics and spurious emissions (2nd–5th harmonic at 4.88–12.2 GHz) on the spectrum analyser.

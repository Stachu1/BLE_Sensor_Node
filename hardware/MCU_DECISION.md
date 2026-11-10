# MCU choice for rev B: TI CC2340R5 (BSN-C23)

Decided 2026-10-30 from the rev A comparison (thesis test T0) of `BSN-C23-A` and `BSN-N54-A`. Application: BTHome
advertising every 5 s or slower, 0 dBm, CR2032, room temperature. **Rev B uses the CC2340R5. The N54 variant stops at
rev A.**

Measurements: [`C23/testing/rev_A/Power`](C23/testing/rev_A/Power/POWER_MEASUREMENTS.md),
[`N54/testing/Power`](N54/testing/Power/POWER_MEASUREMENTS.md), [`C23/testing/rev_A/RF`](C23/testing/rev_A/RF/RF_CARRIER.md),
[`N54/testing/RF`](N54/testing/RF/RF_CARRIER.md).

## Main reasons

1. **The sleep floor decides it at T_adv ≥ 5 s.** The N54 spends 40–50 % less charge per event, but its floor is
   11× higher, and the two cross at about 1.3 s. Model at 3.0 V, standby, DRDY wake, one reading per advert:

   | T_adv | C23 | N54 |
   |---|---|---|
   | 5 s | 3.63 µA | 6.07 µA |
   | 10 s | 2.00 µA | 5.14 µA |
   | 60 s | 0.64 µA | 4.36 µA |

2. **The C23 still wins against the N54's best case.** That case is Rev 2 silicon with X2 fitted and a datasheet
   v1.0 floor of about 1.7 µA, which was never measured. The N54 then ties at 5 s (3.57 µA) and loses at every slower
   interval (2.64 µA at 10 s, 1.86 µA at 60 s).
3. **RF, as a second factor.** With no filter on either board (0 dBm, conducted), both fail the FCC restricted-band
   limit on H3, but the C23 by 0.6 dB and the N54 by 17 dB. The C23 passes with 9.5 dB margin (H5) using the simple
   pi network from TI's reference design, so rev B starts from an RF chain that already works. The N54's PA network
   was adapted from Nordic's reference design with 0402 parts instead of 0201. On this layout it cost 10–11 dB of
   output power, so the N54 harmonics were measured with it bypassed. Getting the N54 to pass would need a new
   filter and another RF iteration. This alone would not have decided it. The power results did.
4. **Cost and RF simplicity:** a cheaper part and a simpler PA network.

## Strengths and weaknesses

C23:

| | Point | Counter-argument |
|---|---|---|
| + | Floor 0.366 µA, below its own datasheet (0.71 µA) | Measured on board #1 only, at room temperature only. On 2026-11-10 board #1 read 0.94 µA and the no-pi board 0.70 µA, cause not known |
| + | Plain standby is enough: no shutdown or cold-boot scheme needed | — |
| − | 12.6 µC per advert and 3.72 µC per DRDY reading (N54: 7.6 and 1.78 µC) | Only matters below about 1.3 s |
| − | −2.1 dBm conducted at the 0 dBm setting | The CR2032's internal resistance limits TX power anyway, and 2 dB of range doesn't matter indoors |
| − | Charge per event +34 % at 2.0 V | N54: +40 % |
| − | Each payload reload costs about 20 µC (found 2026-11-10) | Firmware: one advert per DRDY, or slow readings |
| − | Shutdown floor unresolved | Not needed: standby is already close to shutdown |
| − | Debug state survives a plain power cycle | Only during development (short TP9 to TP10) |

N54:

| | Point | Counter-argument |
|---|---|---|
| + | 40–50 % less charge per advert and per reading | Swamped by the floor at T_adv ≥ 5 s |
| + | 0.0 dBm conducted, about 2 dB more | Same as the C23's −2.1 dBm point |
| + | Full-firmware result matches the model (6.1 against 6.01 µA) | It also confirms the high floor |
| + | Flexible sleep (System OFF with GRTC wake, RAM retention per block) | System OFF still gives 2.2–2.4 µA at 60–120 s |
| − | Floor 4.20 µA, about 1.4 µA above the datasheet on both boards | Possibly erratum 31 (Rev 1 silicon), but even the best case loses (reason 2) |
| − | H3 fails by 17 dB unfiltered | Fixable, but needs a new filter and another RF iteration |
| − | MPSL forces RC calibration on the LFRC | Fit X2, one extra part |

## Update 2026-11-10: the C23 6.55 µA result

On 2026-10-30 the 6.55 µA run (model 3.85 µA) was treated as a measurement or firmware error. **It was neither.**
It repeats (6.5 µA), and the cause is measured: in the TI stack every payload reload costs about **20 µC**
(20.6 µC on board #1, 19.3 µC on the no-pi board), because `GapAdv_prepareLoadByHandle` disables advertising and
`GapAdv_loadByHandle` re-enables it. With that term the C23 model matches all full-firmware runs. The N54 has no
such cost (`bt_le_adv_update_data`), and its numbers stand. Details:
[`C23/testing/rev_A/Power`](C23/testing/rev_A/Power/POWER_MEASUREMENTS.md#payload-reload-2026-11-10).

The C23 column of reason 1 assumed a free reload. With the measured costs, at 3.0 V, in µA:

| T_adv | C23, one advert per DRDY (25.1 µC per event) | C23, periodic, reading every 60 s | N54 measured, reading every 60 s | N54 best case, reading every 60 s |
|---|---|---|---|---|
| 5 s | 5.39 | 3.29 | 5.75 | 3.25 |
| 10 s | 2.88 | 2.03 | 4.99 | 2.49 |
| 60 s | 0.78 | 0.98 | 4.36 | 1.86 |

- **Against the measured N54 the C23 still wins at every interval from 5 s**, with either firmware design.
- **Against the N54 best case** (reason 2, never measured) it ties at 5 s and wins from 10 s, if the C23 firmware
  keeps reloads rare. With a reload every 10 s, as in the current `ble_sensor`, the C23 would lose at 5 s.
- **The choice holds, with a firmware condition:** rev B firmware must avoid frequent reloads (one advert per DRDY,
  or slow readings).

## Carried into rev B

- [ ] Full-firmware check on rev B with the chosen firmware design (one advert per DRDY, or periodic with slow
      readings), against the model with the reload term.
- [ ] Keep the pi network and check the H5 margin with the trace antenna. Radiated pre-scan on the final board.
- [ ] CR2032 VDD dip during TX.
- [ ] N54 floor offset investigation, for the thesis only:
      [`N54/testing/Power`](N54/testing/Power/POWER_MEASUREMENTS.md#floor-offset-investigation-not-needed-for-the-mcu-choice).

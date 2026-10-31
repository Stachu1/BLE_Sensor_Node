# MCU choice for rev B: TI CC2340R5 (BSN-C23)

Decided 2026-10-30 from the rev A comparison (thesis test T0) of `BSN-C23-A` and `BSN-N54-A`. Application: BTHome
advertising every 5 s or slower, 0 dBm, CR2032, room temperature. **Rev B uses the CC2340R5. The N54 variant stops at
rev A.**

Measurements: [`C23/testing/Power`](C23/testing/Power/POWER_MEASUREMENTS.md),
[`N54/testing/Power`](N54/testing/Power/POWER_MEASUREMENTS.md), [`C23/testing/RF`](C23/testing/RF/RF_CARRIER.md),
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
| + | Floor 0.366 µA, below its own datasheet (0.71 µA) | Measured on board #1 only, at room temperature only |
| + | Plain standby is enough: no shutdown or cold-boot scheme needed | — |
| − | 12.6 µC per advert and 3.72 µC per DRDY reading (N54: 7.6 and 1.78 µC) | Only matters below about 1.3 s |
| − | −2.1 dBm conducted at the 0 dBm setting | The CR2032's internal resistance limits TX power anyway, and 2 dB of range doesn't matter indoors |
| − | Charge per event +34 % at 2.0 V | N54: +40 % |
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

## Assumption: the C23 6.55 µA result

The full-firmware run on the C23 no-pi board read 6.55 µA at 5 s against a model of 3.85 µA. It is **treated as a
measurement or firmware error**, for these reasons:

- Board #1's full-firmware result matched the model once the once-a-second reload check was accounted for (that
  check has since been fixed).
- The no-pi board's own floor was never measured.
- A reload retry falling back to 1 s wake-ups would add about 2.2 µA, which accounts for most of the gap.
- The N54 never measured below its model in any configuration.

To be confirmed on rev B. It doesn't block the order.

## Carried into rev B

- [ ] Full-firmware check at 5 s (model 3.85 µA) to close the assumption above.
- [ ] Keep the pi network and check the H5 margin with the trace antenna. Radiated pre-scan on rev C.
- [ ] CR2032 VDD dip during TX.
- [ ] N54 floor offset investigation, for the thesis only:
      [`N54/testing/Power`](N54/testing/Power/POWER_MEASUREMENTS.md#floor-offset-investigation-not-needed-for-the-mcu-choice).

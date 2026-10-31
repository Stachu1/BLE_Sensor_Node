# BSN-N54 (Nordic nRF54L variant)

> **Concluded at rev A.** The N54 was compared with the C23 on rev A, and rev B uses the CC2340R5. See
> [`MCU_DECISION.md`](../MCU_DECISION.md). This folder is kept as the record of that comparison.

KiCad project: `BSN-N54.kicad_pro`. See the root README for the board naming scheme.

## Rev A (`BSN-N54-A`)

Ordered as a separate design from BSN-C23-A (not panelized). Firmware, bring-up procedure and per-board
results: [`firmware/N54`](../../firmware/N54) and [`firmware/N54/BRINGUP.md`](../../firmware/N54/BRINGUP.md).

### Bring-up status

| Board | BLE address | Status |
|---|---|---|
| #1 | EC:A6:80:CE:7A:1A | Full build except U2 (SHTC3) and X2 (32 kHz). `hwtest` 13/13 PASS. `ble_sensor` advertises BTHome and is decoded with `tools/bsn_scan.py`. Antenna side fitted with the C23 values (L6 4.3 nH, 2.1 pF shunt), **not verified on this layout** (see below). PA network as designed, which loses about 10 dB (see board #2). |
| #2 | FA:28:B5:E0:85:F5 | MCU + U.FL, no antenna, no U2/X2. `hwtest` 13/13 PASS. A\*: PA network bypassed. Used for the crystal trim, conducted power and the current measurements. |

### Test results

- **RF:** [`testing/RF/RF_CARRIER.md`](testing/RF/RF_CARRIER.md). HFXO trim 11.75 pF (+127 ppm at the datasheet
  7 pF). The reference PA network as laid out costs 10–11 dB. Bypassed, the PA gives 0.0 dBm at the 0 dBm
  setting and +7.5 dBm at +8 dBm.
- **Current:** [`testing/Power/POWER_MEASUREMENTS.md`](testing/Power/POWER_MEASUREMENTS.md). Floor 4.20 µA
  (System OFF 2.05 µA, both about 1.4 µA above the datasheet on both boards, cause not found), 7.6 µC per advert
  at 0 dBm, 2.01 / 1.78 µC per sensor reading with timer / DRDY wake (C23: 0.366 µA, 12.6 µC, 9.56 / 3.72 µC).

### Rework log

Hand-modified boards are marked `A*` (see the root README).

| Board | Date | Change | Reason |
|---|---|---|---|
| #1 | 2026-10-27 | Antenna side: 4.3 nH series and 2.1 pF shunt (the C23 match) | Same antenna as C23. Not re-matched: AE1 is fed from the other end than on C23 (rotated 180°, feed pad at x = 146.75 instead of 153.25) through a longer trace, so the match is only a starting point |
| #2 | 2026-10-27 | X1 reflowed | Checking the +127 ppm offset (no change) |
| #2 | 2026-10-27 | PA network bypassed: 15 pF in series at L2 (DC block), L3 and L4 bridged, C14, C15, C16 removed. R4 0 Ω and J1 kept | The network cost 10–11 dB. Bypassed, the output matches the datasheet |
| #2 | 2026-10-27 | Cleaned with IPA | Checking whether flux explains the high floor current (no change) |

## ANT-pin matching network

The antenna matching network on the nRF54L05 ANT pin (U1 pin 31) is the Nordic reference PA network (nRF54L
datasheet, circuit configuration 1 for QFN48: L2, C14, L3, C15, L4, C16), followed by the antenna match (L5, L6, L7)
and the U.FL test point (R4, J1).

```
U1.ANT(31) ─ L2 ─┬─ L3 ─┬─ L4 ─┬──────────── L6 ─┬─ AE1
               C14    C15    C16   L5      │     L7
                │      │      │    │      R4     │
              VSS_PA  GND    GND  GND      │    GND
             (pin 32)                     J1
```

| Ref | Value | Role |
|---|---|---|
| L2, C14, L3, C15, L4, C16 | 2.7 nH, 1.5 pF, 3.5 nH, 2.0 pF, 3.5 nH, 0.3 pF | Nordic reference PA network (0201 in the reference, 0402 here) |
| L5 | 7.3 nH | Shunt to GND on the J1 node (antenna side) |
| L6 | 6.7 nH | Series to the antenna |
| L7 | | Shunt at the antenna feed |
| R4, J1 | 0 Ω, U.FL | Test point, not fitted in normal use |

C14 grounds only to pin 32 (VSS_PA), which only joins the centre pad, and C15 grounds straight to the bottom plane
with no inner-layer fill, as Nordic's notes require.

**Measured on rev A:** this network, as laid out with 0402 parts, cost 10–11 dB into 50 Ω (see
[`testing/RF/RF_CARRIER.md`](testing/RF/RF_CARRIER.md)). A rev B N54 should copy Nordic's 0201 layout exactly and
verify the PA network into 50 Ω on its own before the antenna is matched.

### Original Smith chart estimate (superseded)

Before the boards existed, the MCU source impedance and the antenna impedance were estimated from the nRF54L and
antenna datasheets and stepped through all 8 elements on a Smith chart. This treated L5 as a series part, which it
isn't on the board, and the estimated antenna impedance was later measured on C23 to be quite different
(about 6.4 − j13 Ω, see `hardware/C23/testing/RF/ANTENNA_MATCHING.md`). Kept for reference:

https://onlinesmithchart.com/?circuit=blackBox_34.1_-40.9_0__seriesInd_2.7_nH_0_0__shortedCap_1.5_pF_0_0_0__seriesInd_3.5_nH_0_0__shortedCap_2_pF_0_0_0__seriesInd_3.5_nH_0_0__shortedCap_0.3_pF_0_0_0__shortedInd_7.3_nH_0_0__seriesInd_6.7_nH_0_0&fSpan=0

A simplified 3-element equivalent from the same estimate:

https://onlinesmithchart.com/?circuit=blackBox_34.1_-40.9_0__seriesInd_4.2_nH_0_0__shortedCap_0.3_pF_0_0_0__seriesInd_6.7_nH_0_0&fSpan=0

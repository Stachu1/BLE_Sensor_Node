# BSN-C23-B current measurements

Average-current measurements on rev B for T1 (average current at 5 s) and the power model. Same method as rev A
([`../../rev_A/Power/POWER_MEASUREMENTS.md`](../../rev_A/Power/POWER_MEASUREMENTS.md)): the charge of one event
above the floor is `Q = (I_avg − I_floor) × T_event`, measured at a fast event rate.

Raw summary: [`power_2026-11-20.csv`](power_2026-11-20.csv).

## Session 2026-11-20, B #1

B #1 on a bench PSU at 2.969 V, 0 dBm, `LOG=0 RELOAD=0` (one advert per DRDY, payload written in place).

- **Meter range:** 1 mA for the floor (a lower range gave random overloads), 10 mA for F2 and F3.
- **Reset before each reading** (as on rev A): J-Link unplugged, VDD shorted to GND for about 1 s, supply
  reconnected, about 10 s for the current to settle, then the reading.

| # | Build | Mean | σ | n | SEM | Event period | Charge per event |
|---|---|---|---|---|---|---|---|
| F1 | standby floor (`pwrtest standby`) | 0.684 µA | 0.077 µA | 395 | 0.004 µA | – | – |
| F2 | `ble_sensor DRDY=7` (0.2 s) | 105.8 µA | 17.4 µA | 275 | 1.05 µA | 202.7 ms | **21.3 ± 0.2 µC** |
| F3 | `ble_sensor DRDY=4` (5 s) | **4.357 µA** | 4.489 µA | 1010 | 0.141 µA | 5.07 s | 18.6 ± 0.7 µC |

- **Measured 5 s average: 4.36 ± 0.14 µA** (F3, error is the SEM only).
- **Model from F2:** 0.684 + 21.3 / 5.07 = **4.89 µA**. The measured value is 0.53 µA lower, about 3.7 SEM.
  The two charge values (21.3 and 18.6 µC) do not agree. Cause not investigated. Candidates: the event periods
  are taken from rev A (2026-11-10) and not measured on this board, the HDC2010 internal timer differs between
  parts, and the 5 s readings have σ near the mean (as on rev A, cause not investigated).
- With the nominal periods (200 ms, 5 s) the charge is 21.0 µC and the model 4.89 µA, so the gap does not come
  from the period rounding.
- Against rev A board #1 (2026-11-12, same build): 21.1 ± 1.2 µC per event at 0.2 s, 4.83 ± 0.34 µA at 5 s. The
  rev B floor (0.684 µA) is just below the 0.7–0.8 µA taken for rev A on 2026-11-12. The rev A 0.366 µA reading of
  2026-10-26 is treated as a mistake, as it could not be reproduced.

## Session 2026-11-23, B #2

B #2 (one 100 µF bulk cap) on a bench PSU at 3.002 V, 0 dBm, same builds as B #1. Meter range and reset method
not noted. Raw summary: [`power_2026-11-23.csv`](power_2026-11-23.csv).

| # | Build | Mean | σ | n | SEM | Event period |
|---|---|---|---|---|---|---|
| F1 | standby floor (`pwrtest standby`) | 0.682 µA | 0.056 µA | 250 | 0.0035 µA | – |
| F2 | `ble_sensor DRDY=7` (0.2 s) | 99.3 µA | 6.735 µA | 600 | 0.27 µA | 209.96 ± 0.6 ms (NINA) |
| F3 | `ble_sensor DRDY=4` (5 s) | **4.391 µA** | 4.533 µA | 930 | 0.149 µA | 5.2545 s (soak) |

- The floor agrees with B #1 (0.684 µA) within 0.002 µA, so the 100 µF cap adds no leakage this run can see.
- The 0.2 s period is from the packet id against time in [`b2_drdy7.csv`](b2_drdy7.csv) (NINA, 13:14–13:20,
  544 adverts, 1658 ids). The ± 0.6 ms comes from the 1 s timestamps over 348 s. The ratio to nominal is 1.050 at
  0.2 s and 1.051 at 5 s, so on B #2 both settings run about 5 % slow by the same factor.

## B #1 0.2 s period (2026-11-23)

From [`b1_drdy7.csv`](b1_drdy7.csv) (NINA, 15:14–15:19, 817 adverts, 1655 ids): **200.74 ± 0.6 ms**. It replaces
the 202.7 ms taken from rev A for F2 above. Ratio to nominal 1.004 at 0.2 s and 1.007 at 5 s (soak). On B #2 the
two ratios are 1.050 and 1.051. The B #1 difference (0.4 %) is about the size of the timestamp uncertainty
(0.3 %), so the two settings likely share one factor on both boards, not shown beyond that.

## T1 result: model against measurement, both boards (2026-11-23)

All periods measured on the board itself (0.2 s from the NINA logs above, 5 s from the soak). Calculation by the
author, checked with more digits. Errors are 1σ from the SEM of each reading and ±0.6 ms on the 0.2 s period
(1 s timestamps over about 340 s). The 5 s period error (60 h of data) is negligible.

- Charge per event: Q = (F2 − F1) × T(0.2 s). Energy per event: E = Q × V.
- Model at 5 s: I = F1 + Q / T(5 s). Power: P = I × V.

| | B #1 (2.969 V) | B #2 (3.002 V) |
|---|---|---|
| Charge per event Q | 21.10 ± 0.22 µC | 20.71 ± 0.08 µC |
| Energy per event E | 62.65 ± 0.65 µJ | 62.16 ± 0.25 µJ |
| Model 5 s average | 4.874 ± 0.044 µA (14.47 ± 0.13 µW) | 4.623 ± 0.016 µA (13.88 ± 0.05 µW) |
| **Measured 5 s average (F3)** | **4.357 ± 0.141 µA (12.94 ± 0.42 µW)** | **4.391 ± 0.149 µA (13.18 ± 0.45 µW)** |
| Measured − model | −0.52 ± 0.15 µA (−10.6 %, 3.5σ) | −0.23 ± 0.15 µA (−5.0 %, 1.5σ) |
| Charge per event from F3, (F3 − F1) × T(5 s) | 18.50 ± 0.71 µC | 19.49 ± 0.78 µC |

- On both boards the measured 5 s average is below the model built from the 0.2 s run. On B #1 the gap is 3.5σ,
  on B #2 it is 1.5σ, so B #2 alone does not show it.
- Put the other way, an event seems to cost less charge at 5 s than at 0.2 s (B #1 2.6 ± 0.7 µC less, B #2
  1.2 ± 0.8 µC less). One reading is that waking more often has an extra cost per event that the linear model
  does not include, for example the device not reaching its full standby state between events 0.2 s apart. Not
  investigated. Other candidates, also not investigated: how the meter samples the 5 s current (σ is about the
  mean at 5 s) and the different supply voltages of the two sessions.
- The linear model from the 0.2 s run is therefore an upper bound on these two boards, by about 5 to 11 %.
- The model numbers in this table replace the 20 Nov B #1 values above (21.3 µC, 4.89 µA), which used the rev A
  periods.

## DRDY periods from the soak (2026-11-20 to 2026-11-23)

The 5 s period of each soak node, from the packet id against the scanner time over about 60 h (from 22:00 on
20 Nov, after the last reflash). The packet id counts DRDY events, so lost adverts do not change it. The nodes
ran on CR2032 cells in the flat, not on the bench PSU.

| Node | Period |
|---|---|
| B #1 | 5.0366 s |
| B #2 | 5.2545 s |
| B #3 | 4.8131 s |
| B #6 | 5.3428 s |
| B #8 | 5.1257 s |
| B #9 | 5.2336 s |
| A #1 | 5.0911 s |
| A #2 | 5.1530 s |

The spread is 4.81 to 5.34 s (about ±5 %). It comes from the HDC2010 internal timer (likely, not
investigated). The rev A value of 5.07 s used for B #1 above was therefore not this board's period.

## Open

- Why the 5 s average is below the model (see T1 result). A third rate (`DRDY=5`, 1 s) on one board would show
  whether the charge per event changes with the rate.
- The F3 periods above are from the cell at room temperature in the flat, not from the bench run. Likely close,
  not checked.

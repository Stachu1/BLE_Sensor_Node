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

## Open

- Measure the DRDY periods on rev B (count adverts over a fixed time with the scanner, or `sensorEvents` over
  the J-Link), then recompute F2 and F3.
- Repeat F3 on a second board (T1 asks for two).

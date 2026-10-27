# BSN-N54-A current measurements (2026-10-27)

Measurements on board #2 for the MCU comparison with BSN-C23, using the method, meter and formula of
[`hardware/C23/testing/Power/POWER_MEASUREMENTS.md`](../../../C23/testing/Power/POWER_MEASUREMENTS.md):

```
I_avg = I_floor + Q_adv / T_adv + Q_sensor / T_sensor
```

## Results

| Quantity | N54 (board #2) | C23 (board #1) |
|---|---|---|
| **Sleep floor** (System ON idle, RC LF clock, sensors asleep) | **4.16 µA** | 0.366 µA |
| **System OFF** | **2.05 µA** | unresolved |
| **Advertising event**, 0 dBm, 3 channels, 31-byte BTHome payload | **7.6 µC** | 12.6 µC |
| Adverts only, 1 s interval | 4.16 + 7.6 = **11.7 µA** | 0.37 + 12.5 = 12.9 µA |
| Adverts only, 2 s interval | 7.9 µA | 6.6 µA |

The N54 spends about 40 % less charge per advert, the C23 sleeps far more cheaply. With these floors the
break-even is an advertising interval of about **1.3 s**: faster favours the N54, slower the C23. If the N54 floor
came down to its datasheet value (about 2 µA), the break-even would move to about 3 s.

## Setup

- **Board:** BSN-N54-A #2. U2 (SHTC3) and X2 (32.768 kHz) are not fitted; the LF clock is the internal RC, as on
  C23. The PA network is bypassed (see [`../RF/RF_CARRIER.md`](../RF/RF_CARRIER.md)), and **J1 is terminated with a
  50 Ω broadband load**, so the PA sees the load the datasheet assumes. Board #1 still has the mismatched network,
  which raised the TX current, so it was not used.
- **Supply:** bench PSU at 3.0 V on TP1/TP4.
- **Meter:** Keysight 34461A in series. µA range for the floors, 10 mA range for advertising.
- **Procedure:** as for C23. After every flash, unplug all J-Link wires, short TP1 to TP4 for about 1 s, power
  on, wait at least 10 s.
- **Firmware:** `firmware/N54` (NCS v3.4.0), `LFCLK=rc`, HFXO trim 11.75 pF.

## Sleep floor

| # | Build | RC calibration | Mean | σ | n |
|---|---|---|---|---|---|
| F1 | `pwrtest MODE=standby` | NCS default: temperature every 4 s, recalibrate at least every 8 s | 4.89 µA | 3.08 µA | 750 |
| F2 | `pwrtest MODE=standby` | rare: temperature every 63 s | 4.155 µA | 0.096 µA | 700 |
| F3 | `pwrtest MODE=standby`, board cleaned with IPA | rare: temperature every 8 s | ≈ 4.2 µA, jumps to ~6 µA every few seconds | | |
| S1 | `pwrtest MODE=shutdown` (System OFF) | — | **2.048 µA** | 0.04 µA | 400 |

- **The default RC calibration costs about 0.7 µA.** It starts the HFXO every few seconds, which also caused the
  large σ in F1. All N54 builds now use the rarest calibration the BLE stack accepts (`common/lfrc.conf`).
- **About 1.4 µA above the datasheet in both states:** System OFF reads 2.05 µA against 0.6 µA, and System ON
  4.16 µA against about 2.0 µA (96 KB RAM). An offset present even in System OFF is either on the board, or something
  Zephyr leaves on in System OFF (RAM retention, GRTC).
- **Not flux:** the board had flux from reworking X1 and the PA network, but cleaning it with IPA changed nothing (F3).
- **Not the HDC2010:** `pwrtest standby` doesn't touch it (it powers up idle at about 50 nA), and the same firmware
  gives C23 its 0.366 µA floor with the same sensor.

## Advertising

`ble_sensor LOG=0 SENSOR_S=0`, 0 dBm, legacy non-connectable, 3 channels, 31-byte BTHome payload. Period = interval
+ 5 ms (mean `advDelay`).

| # | ADV_MS | Period | RC calibration | Mean | σ | n | Floor used | Q_adv |
|---|---|---|---|---|---|---|---|---|
| A1 | 50 | 55 ms | default (as F1) | 142 µA | 31.8 µA | 500 | 4.89 µA (F1) | **7.54 ± 0.08 µC** |
| A2 | 100 | 105 ms | rare (8 s) | 76.5 µA | 21 µA | 500 | 4.155 µA (F2) | **7.60 ± 0.10 µC** |

A1 and A2 agree within 1 %, with the floor measured under the same calibration setting in each case.
**Q_adv = 7.6 µC at 0 dBm and 3.0 V.**

## Pitfalls

- **MPSL limits on RC calibration:** the BLE stack refuses to build with RC calibration off ("MPSL requires clock
  calibration to be enabled when RC is used as LFCLK"), and a calibration period above 8 s (`rc_ctiv` > 32) makes
  `bt_enable()` fail at run time. With `LOG=0` the node then sits idle at the floor current and never advertises,
  which is what the first A2 attempt read (≈ 4.2 µA).
- **Current limit:** see [`../RF/RF_CARRIER.md`](../RF/RF_CARRIER.md). 20 mA is too low for +8 dBm.

## Open items

- [ ] Find the extra ~1.4 µA: measure board #1's floors (no rework), and check what Zephyr keeps powered in
      System OFF on the nRF54L (RAM retention, GRTC).
- [ ] Find the wake-ups every few seconds in standby (F3).
- [ ] Advertising at +8 dBm, sensor reading (`MODE=sensor`, `sensor_irq`), floor with the BLE stack idle (`ADV=0`).
- [ ] Shutdown with DRDY wake-up: needs the cold boot + BLE start + advert burst charge, a new `pwrtest` mode.

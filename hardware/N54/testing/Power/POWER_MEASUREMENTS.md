# BSN-N54-A current measurements (2026-10-27, 2026-10-30)

Measurements on board #2 for the MCU comparison with BSN-C23, using the method, meter and formula of
[`hardware/C23/testing/Power/POWER_MEASUREMENTS.md`](../../../C23/testing/Power/POWER_MEASUREMENTS.md):

```
I_avg = I_floor + Q_adv / T_adv + Q_sensor / T_sensor
```

## Results

All at 3.0 V and 0 dBm unless noted. The 2026-10-30 values (34465A) are the reference set.

| Quantity | N54 (board #2) | C23 (board #1) |
|---|---|---|
| **Sleep floor** (System ON idle, RC LF clock, sensors asleep) | **4.20 µA** (4.93 µA at 2.4 V, 5.67 µA at 2.0 V) | 0.366 µA |
| **System OFF** | **2.05 µA** (≈ 1.9 µA with every GPIO reset) | unresolved |
| **Advertising event**, 3 channels, 31-byte BTHome payload | **7.58 µC** (10.58 µC at 2.0 V) | 12.6 µC (16.9 µC at 2.0 V) |
| **Sensor reading**, MCU timer + wait (as in `ble_sensor`) | **2.01 µC** | 9.56 µC |
| **Sensor reading**, HDC2010 auto mode, DRDY wakes the MCU | **1.78 µC** | 3.72 µC |
| **Full firmware**, 5 s advertising, sensor every 10 s | **6.1 µA** (model 6.01 µA, J1 open, see below) | 6.55 µA on the no-pi board (model 3.85 µA, unresolved) |

The N54 spends about 40 % less charge per advert and 50–80 % less per sensor reading, but its floor is 3.8 µA
higher. With these values the break-even advertising interval is about **1.3 s**: faster favours the N54, slower
the C23. For the application (advertising every 5 s or slower) the floor dominates.

## Setup

- **Board:** BSN-N54-A #2. U2 (SHTC3) and X2 (32.768 kHz) are not fitted; the LF clock is the internal RC, as on
  C23. The PA network is bypassed (see [`../RF/RF_CARRIER.md`](../RF/RF_CARRIER.md)), and **J1 is terminated with a
  50 Ω broadband load**, so the PA sees the load the datasheet assumes. Board #1 still has the mismatched network,
  which raised the TX current, so it was not used for advertising.
- **Supply:** bench PSU on TP1/TP4.
- **Meter:** in series. 2026-10-27: Keysight 34461A. **2026-10-30: Keysight 34465A** (periodically calibrated, the
  most trusted of the meters used). µA range for the floors, 1 mA for the sensor modes, 10 mA for advertising.
  Normal mode is NPLC 10 with autozero (about 150 readings per minute); the full-firmware check used NPLC 100 with
  autozero off, so each reading integrates about 2 s with almost no gap.
- **Procedure:** as for C23. After every flash, unplug all J-Link wires, short TP1 to TP4 for about 1 s, power
  on, wait at least 10 s.
- **Firmware:** `firmware/N54` (NCS v3.4.0), `LFCLK=rc`, rare RC calibration (`common/lfrc.conf`), HFXO trim 11.75 pF.
  From 2026-10-30 the HDC2010 INT pin uses the GPIO SENSE mechanism (`sense-edge-mask` in `common/bsn_n54.overlay`)
  instead of a GPIOTE IN channel.

## Sleep floor

| # | Date | Build | RC calibration | V | Mean | σ | n |
|---|---|---|---|---|---|---|---|
| F1 | 10-27 | `pwrtest MODE=standby` | NCS default: temperature every 4 s, recalibrate at least every 8 s | 3.0 | 4.89 µA | 3.08 µA | 750 |
| F2 | 10-27 | `pwrtest MODE=standby` | rare: temperature every 63 s | 3.0 | 4.155 µA | 0.096 µA | 700 |
| F3 | 10-27 | `pwrtest MODE=standby`, board cleaned with IPA | rare: temperature every 8 s | 3.0 | ≈ 4.2 µA, jumps to ~6 µA every few seconds | | |
| F4 | 10-30 | `pwrtest MODE=standby` | rare (8 s) | 3.0 | **4.20 µA** | 0.22 µA | 300 |
| F5 | 10-30 | `pwrtest MODE=standby` | rare (8 s) | 2.4 | **4.93 µA** | 0.65 µA | 300 |
| F6 | 10-30 | `pwrtest MODE=standby` | rare (8 s) | 2.0 | **5.67 µA** | 0.31 µA | 300 |
| S1 | 10-27 | `pwrtest MODE=shutdown` (System OFF) | — | 3.0 | **2.048 µA** | 0.04 µA | 400 |
| S2 | 10-28 | `pwrtest MODE=bareoff` (System OFF, every GPIO reset to default first) | — | 3.0 | ≈ 1.9 µA | | |

- **The default RC calibration costs about 0.7 µA.** It starts the HFXO every few seconds, which also caused the
  large σ in F1. All N54 builds now use the rarest calibration the BLE stack accepts (`common/lfrc.conf`).
- **The floor rises as the supply falls**, roughly at constant power (12.6 / 11.8 / 11.3 µW at 3.0 / 2.4 / 2.0 V),
  like the advertising charge. The battery model has to use the floor at the cell voltage, not the 3.0 V value.
- **About 1.4 µA above the datasheet in both states:** System OFF reads 2.05 µA against 0.6 µA, and System ON
  4.2 µA against about 2.0 µA (96 KB RAM). Ruled out:
  - **Pin configuration:** with every GPIO reset to its power-on default (S2) System OFF only drops by about 0.15 µA.
  - **This board's rework:** board #1 (no rework) shows the same offset.
  - **Flux:** cleaning board #2 with IPA changed nothing (F3).
  - **The HDC2010 and the bulk capacitor:** the same HDC2010 and the same 100 µF MLCC (GRM21BR60J107) sit on BSN-C23,
    whose whole floor is 0.366 µA.

  The cause is not found, but it is the same on both boards and with every firmware, so **the measured values are
  used for the comparison and the battery model.**

## Advertising

`ble_sensor LOG=0 SENSOR_S=0 ADV_MS=50` unless noted, 0 dBm, legacy non-connectable, 3 channels, 31-byte BTHome
payload. Period = interval + 5 ms (mean `advDelay`). Floor subtracted at the same supply voltage (2.7 V
interpolated between F4 and F5).

| # | Date | J1 | V | Mean | σ | n | Floor used | Q_adv |
|---|---|---|---|---|---|---|---|---|
| A1 | 10-27 | 50 Ω | 3.0 | 142 µA | 31.8 µA | 500 | 4.89 µA (F1, default calibration) | 7.54 ± 0.08 µC |
| A2 | 10-27 | 50 Ω | 3.0 | 76.5 µA (`ADV_MS=100`, 105 ms) | 21 µA | 500 | 4.155 µA (F2) | 7.60 ± 0.10 µC |
| V1 | 10-30 | 50 Ω | 3.0 | 142 µA | 31 µA | 200 | 4.20 µA | **7.58 ± 0.12 µC** |
| V2 | 10-30 | 50 Ω | 2.7 | 153 µA | 35 µA | 200 | 4.57 µA | **8.16 ± 0.14 µC** |
| V3 | 10-30 | 50 Ω | 2.4 | 165 µA | 37 µA | 200 | 4.93 µA | **8.80 ± 0.14 µC** |
| V4 | 10-30 | 50 Ω | 2.0 | 198 µA | 43 µA | 200 | 5.67 µA | **10.58 ± 0.17 µC** |
| O1 | 10-30 | open | 3.0 | 151 µA | 34 µA | 300 | 4.20 µA | 8.07 ± 0.11 µC |
| O2 | 10-30 | open | 2.7 | 160 µA | 39 µA | 300 | 4.57 µA | 8.55 ± 0.12 µC |
| O3 | 10-30 | open | 2.4 | 177 µA | 41 µA | 300 | 4.93 µA | 9.46 ± 0.13 µC |
| O4 | 10-30 | open | 2.0 | 208 µA | 45 µA | 300 | 5.67 µA | 11.13 ± 0.14 µC |

- **Q_adv = 7.6 µC at 0 dBm and 3.0 V**, the same on both days and both meters.
- **Against supply voltage:** +8 / +16 / +40 % at 2.7 / 2.4 / 2.0 V. The C23 rises by +10 / +20 / +34 %: both DC/DC
  converters draw roughly constant power.
- **J1 left open** (O1–O4, by mistake) costs 5–7 % more charge per advert: the PA sees a full reflection instead of
  50 Ω. The trend against voltage is the same.

## Sensor readings

2026-10-30, 3.0 V, 1 mA range. The event rate was read from `sensorEvents` over the J-Link (without halting), 30 s
apart, after the current reading. Floor subtracted: 4.20 µA (F4).

| # | Build | Mean | σ | n | Event period | Charge per reading |
|---|---|---|---|---|---|---|
| R1 | `pwrtest MODE=sensor PERIOD_MS=97` | 24.4 µA | 0.6 µA | 300 | 99.7 ms (301 in 30 s) | **2.01 ± 0.01 µC** |
| R2 | `pwrtest MODE=sensor_irq HDC_AMM=7` | 13.0 µA | 1.8 µA | 300 | 202.7 ms (148 in 30 s, 0 errors) | **1.78 ± 0.02 µC** |

- **R1:** VDD read, HDC2010 trigger over I2C, 2 ms wait, result read, as on C23 (9.56 µC there).
- **R2:** the HDC2010 runs on its own clock (202.7 ms, the same as the HDC2010 on C23 board #1) and DRDY wakes the
  MCU (3.72 µC on C23).
- On the N54 a timer wake costs only about 0.2 µC more than the DRDY wake. On the C23 every standby exit is
  expensive, so the wake source matters much more there.

## Full-firmware check

2026-10-30, `ble_sensor LOG=0 ADV_MS=5000 SENSOR_S=10`, 3.0 V, 10 mA range, **NPLC 100, autozero off**, about 7 min
(200 readings, steady). **J1 was open** (as O1–O4).

| Measured | Model | Difference |
|---|---|---|
| **6.1 µA** | 4.20 + 8.07 / 5.005 + 2.01 / 10 = **6.01 µA** | +1.5 % |

The model holds for the N54. With J1 terminated (7.58 µC) the same model gives 5.92 µA.

## Pitfalls

- **MPSL limits on RC calibration:** the BLE stack refuses to build with RC calibration off ("MPSL requires clock
  calibration to be enabled when RC is used as LFCLK"), and a calibration period above 8 s (`rc_ctiv` > 32) makes
  `bt_enable()` fail at run time. With `LOG=0` the node then sits idle at the floor current and never advertises,
  which is what the first A2 attempt read (≈ 4.2 µA).
- **Current limit:** see [`../RF/RF_CARRIER.md`](../RF/RF_CARRIER.md). 20 mA is too low for +8 dBm.
- **J1 open:** check the 50 Ω load before every advertising measurement (O1–O4).

## Open items

- [ ] Sensor readings at 2.0 V (assumed to scale like the advertising charge until measured).
- [ ] Optional: full-firmware check with J1 terminated (model 5.92 µA).
- [ ] Optional: the wake-ups every few seconds in standby (F3), X2 fitted (`LFCLK=xtal`, an advantage the C23 doesn't
      need), System OFF with DRDY wake-up (cold boot + BLE start + advert, a new `pwrtest` mode).

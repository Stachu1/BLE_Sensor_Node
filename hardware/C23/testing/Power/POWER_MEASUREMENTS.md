# BSN-C23-A current measurements

Average-current measurements on board #1 (2026-10-26), for the battery-life model, the comparison with the N54
variant and the settings trade-offs:

```
I_avg = I_floor + Q_adv / T_adv + Q_sensor / T_sensor
```

Each `Q` is the charge of one event above the floor. It is measured as an average current at a known, fast event
rate, so a slow, precise ammeter is enough: `Q = (I_avg − I_floor) × T_event`.

Raw summary of every reading: [`power_2026-10-26.csv`](power_2026-10-26.csv).

## Results

All at 3.0 V (3.04 V at TP9) unless noted.

| Quantity | Value | Firmware |
|---|---|---|
| **Sleep floor** (standby, RTC on LFOSC, both sensors asleep, BLE stack idle or not) | **0.366 ± 0.012 µA** | `pwrtest standby`, `ble_sensor ADV=0` |
| **Advertising event**, 0 dBm, 3 channels, 31-byte BTHome payload | **12.6 µC** | `ble_sensor` |
| Advertising event at −8 / +4 / +8 dBm | 11.6 / 18.0 / 27.3 µC | `ble_sensor` |
| Advertising event at 2.7 / 2.4 / 2.0 V (0 dBm) | 13.9 / 15.1 / 16.9 µC | `ble_sensor` |
| **Sensor reading**, MCU timer + 2 ms wait (as in `ble_sensor`) | **9.56 µC** | `pwrtest sensor` |
| **Sensor reading**, HDC2010 auto mode, DRDY wakes the MCU from standby | **3.72 µC** | `pwrtest sensor_irq` |
| Sensor reading, HDC2010 auto mode, DRDY wakes the MCU from shutdown (full reboot) | 15.2–15.3 µC | `pwrtest shutdown_wake` |
| Bare timer wake-up from standby (derived from the full-firmware check) | ≈ 2.4 µC | `ble_sensor` |
| Shutdown floor | **unresolved** (0.42 and 0.9 µA) | `pwrtest shutdown` |
| SHTC3 (U2) left idle after power-on | +43 µA (fixed in firmware) | |
| **Full firmware**: 1 s advertising, sensor every 10 s, 0 dBm | **16.1 ± 0.8 µA** (model: 13.9 µA + the 1 s wake-ups) | `ble_sensor` |

## Setup

- **Board:** BSN-C23-A #1 (A\*). **U2 (SHTC3) is fitted**, although the BOM marks it DNP. The antenna side is
  matched: L2 = 4.3 nH, 2.1 pF on the L3 pads, fitted before any of these measurements. The PA-side pi network is
  the TI reference (C7/C8 1.5 pF, L1 2.8 nH).
- **Supply:** bench PSU on TP9/TP10, no coin cell. 3.04 V at TP9 unless noted.
- **Meter:** Keysight 34461A in series, DC current, fixed range, about 150 samples per minute. Mean and standard
  deviation from its statistics. Range: µA for the floors, 1 mA for the `pwrtest` event modes, 10 mA for anything
  with the radio or a reboot (the 1 mA range overloads on those peaks).
- **Event rates** were measured, not assumed, where the firmware can count. `sensorEvents` was read twice, 30 s
  apart, over the J-Link without halting (`mem32`). The advertising period is the interval plus 5 ms, the mean of
  the 0–10 ms random `advDelay` that BLE adds to every event.

### Procedure for each reading

1. Meter on the 10 mA range (or bypassed) and the J-Link connected, then `make jflash ...`.
2. Unplug **all** J-Link wires.
3. PSU off, then **short TP9 to TP10 for about 1 s**.
4. PSU on, wait at least 10 s (every `pwrtest` build waits 5 s after boot).
5. Set the range and take the samples.

Step 3 matters. After a debug session the CC23xx only fakes standby, so the debugger can stay attached, and that
state survives anything short of a full power-on reset. With the meter in series, switching the PSU off is not
always enough: C5 (100 µF) only discharges through the board. The first floor measurements were taken without
the short and read 0.925 µA (standby). With the short, the same build reads 0.366 µA. See [Pitfalls](#pitfalls).

### Why the event modes run fast

The meter integrates each reading over a short window with gaps in between. One event per second is a pulse of a
few ms that most readings miss and a few catch in full. In the first `sensor` attempt (1 s period) that gave
σ = 112 µA on a mean of 7.7 µA, an uncertainty of ±5 µA on the mean. The 200 ms advertising point (about one event
per reading) came out 12 % low. Running the events at 5–20 Hz puts several events in every reading. The charge per
event does not change, because the MCU still reaches standby between events with more than 40 ms to spare. The
polling period is 97 ms rather than 100 ms so it cannot lock to the meter's sample clock; advertising is already
randomised by `advDelay`.

## Sleep floor

| # | Build | Reset | Mean | σ | n | σ_mean |
|---|---|---|---|---|---|---|
| F1 | `pwrtest standby`, before the SHTC3 fix | PSU off/on | 44 µA | — | 1 | — |
| F2 | `pwrtest standby` | PSU off/on | 0.925 µA (superseded) | 0.293 µA | 500 | 0.013 µA |
| F3 | `ble_sensor LOG=0 SENSOR_S=0 ADV=0` (stack running, no advertising) | PSU off/on | 0.367 µA | 0.300 µA | 500 | 0.013 µA |
| F4 | `pwrtest standby` | **TP9 short** | **0.366 µA** | 0.290 µA | 600 | 0.012 µA |

- **The floor is 0.366 µA**, with or without the BLE stack running. Readings jump between about 0 and 1 µA because
  the CC2340 wakes briefly for regulator recharge and RC-oscillator calibration. The mean is the number to use.
- **F2** was the same build and pin setup as F4. The difference is put down to the reset (the debug logic still
  powered). It is kept here only as a warning.
- **Breakdown:** 0.366 µA is lower than the datasheet typicals for the CC2340R5 in standby (0.71 µA) plus the SHTC3
  asleep (0.3 µA) plus the HDC2010 (0.05 µA). This part and these sensors beat their typicals at room temperature,
  so there is no measurable flux leakage.
- **To do:** re-measure with U2 removed and the board cleaned.

### Shutdown floor (unresolved)

| # | Build | Reset | Mean | σ | n |
|---|---|---|---|---|---|
| S1 | `pwrtest shutdown` | PSU off/on | 0.420 µA | 0.052 µA | 500 |
| S2 | `pwrtest shutdown` | TP9 short | ≈ 0.9 µA | — | — |

Both values are above or near the standby floor, which shutdown should be well below. The firmware cannot yet tell
whether `Power_shutdown()` was refused, and probing over SWD does not help: SWD activity wakes the CC23xx from
shutdown (`PowerLPF3_RESET_SHUTDOWN_SWD`). Next step: record the reset reason and a "shutdown refused" counter in
retained memory, and read them after the measurement. Until then the shutdown-based results (S1/S2, the
`shutdown_wake` floor and the standby/shutdown break-even) are pending.

## Sensor readings

| # | Build | Range | Mean | σ | n | Event period | Charge per reading |
|---|---|---|---|---|---|---|---|
| R1 | `pwrtest sensor PERIOD_MS=1000` | 1 mA | 7.7 µA | 112 µA | 500 | 1.0 s | superseded (±5 µC) |
| R2 | `pwrtest sensor PERIOD_MS=97` | 1 mA | 95.0 µA | 0.8 µA | 500 | 101.0 ms (297 in 30 s) | **9.56 ± 0.04 µC** |
| R3 | `pwrtest sensor_irq HDC_AMM=7` | 1 mA | 18.7 µA | 15.8 µA | 500 | 202.7 ms (148 in 30 s) | **3.72 ± 0.15 µC** |
| R4 | `pwrtest shutdown_wake HDC_AMM=7` | 10 mA | 76 µA | 72 µA | 800 | 202.7 ms (as R3) | 15.2–15.3 ± 0.5 µC |

Floor subtracted: 0.366 µA (R2, R3). For R4 it is the unresolved shutdown floor (0.4–0.9 µA), which moves the
result by less than 0.1 µC.

- **R2:** VDDS read, HDC2010 trigger over I2C, 2 ms `usleep`, result read. That is two standby entries and exits
  per reading. Each reading takes about 4 ms on top of the 97 ms sleep.
- **R3:** no trigger write, no 2 ms wait, no VDDS read, and one standby cycle per reading. The HDC2010's own
  oscillator runs 1.4 % slow (202.7 ms instead of 200 ms). Readings were valid (22.7 °C, 43.0 %RH, no I2C errors).
- **R4:** every reading is a full cold boot (ROM, C startup, FreeRTOS, GPIO/I2C init), then the read and shutdown.
  RAM is lost in shutdown, so the rate could not be read back; it is the same HDC2010 clock as R3.

**Trade-off:**

| Method | Charge per reading | Added at a 10 s period | at 60 s |
|---|---|---|---|
| Timer polling (current `ble_sensor`) | 9.56 µC | 0.96 µA | 0.16 µA |
| DRDY wake from standby | **3.72 µC** | **0.37 µA** | 0.06 µA |
| DRDY wake from shutdown | 15.2 µC | 1.52 µA | 0.25 µA |

- **The DRDY interrupt saves 61 % per reading.** Polling costs more than the wait itself would suggest, because
  each standby entry and exit costs charge (about 2.4 µC, see the full-firmware check).
- **Shutdown** only pays off if it saves more floor current than the reboot costs (about 11.5 µC more per wake).
  The break-even waits on the shutdown floor. A real node would also have to start the BLE stack on every wake.
- **Not measured yet:** HDC2010 threshold interrupts (wake only on a change).

## Advertising

`ble_sensor LOG=0 SENSOR_S=0`: the sensor is read once at boot, then only the stack and the advertising run. Legacy
non-connectable, all three channels, 31-byte BTHome payload. Floor 0.366 µA, period = interval + 5 ms.

### Interval (0 dBm, 3.04 V)

| # | ADV_MS | Period | Mean | σ | n | Q_adv |
|---|---|---|---|---|---|---|
| A1 | 50 | 55 ms | 230 µA | 47 µA | 500 | **12.63 ± 0.12 µC** |
| A2 | 100 | 105 ms | 119.5 µA | 33 µA | 500 | **12.51 ± 0.16 µC** |
| A3 | 200 | 205 ms | 54.5 µA | 57.2 µA | 500 | 11.10 ± 0.52 µC (superseded) |

A1 and A2 agree within 1 %. A3 had about one event per meter reading and is excluded (see
[Why the event modes run fast](#why-the-event-modes-run-fast)). **Q_adv = 12.6 µC at 0 dBm and 3.0 V.**

### Supply voltage (0 dBm, 50 ms)

| # | V at TP9 | Mean | σ | n | Q_adv | Energy (Q × V) |
|---|---|---|---|---|---|---|
| A1 | 3.04 V | 230 µA | 47 µA | 500 | 12.63 ± 0.12 µC | 38.4 µJ |
| V1 | 2.73 V | 253 µA | 55 µA | 500 | 13.89 ± 0.14 µC | 37.9 µJ |
| V2 | 2.42 V | 275 µA | 58 µA | 500 | 15.10 ± 0.14 µC | 36.5 µJ |
| V3 | 2.01 V | 308 µA | 70 µA | 500 | 16.92 ± 0.17 µC | 33.9 µJ |

The DC/DC converter draws roughly constant power, so the charge per advert rises as the battery voltage falls:
**+34 % from 3.0 V to 2.0 V**. The battery-life model has to integrate over the CR2032 discharge curve rather than
use the 3 V value. The floor was assumed constant (0.366 µA) for these points. Its own voltage dependence is not
measured yet, and it changes Q by less than 0.02 µC.

### TX power (50 ms, 3.04 V)

| # | TX_DBM | Mean | σ | n | Q_adv | vs 0 dBm | Adverts only, 1 s interval |
|---|---|---|---|---|---|---|---|
| P1 | −8 | 212 µA | 47 µA | 500 | 11.64 ± 0.14 µC | −8 % | 11.6 µA |
| A1 | 0 | 230 µA | 47 µA | 500 | 12.63 ± 0.12 µC | — | 12.6 µA |
| P2 | +4 | 327 µA | 72 µA | 500 | 17.96 ± 0.18 µC | +42 % | 17.9 µA |
| P3 | +8 | 497 µA | 110 µA | 500 | 27.32 ± 0.27 µC | +116 % | 27.2 µA |

The TX power setting is rounded down to the stack's PA table. Below 0 dBm the fixed cost of each event
dominates (wake-up, HFXT start, radio setup, stack processing), so −8 dBm saves only 8 %. Above 0 dBm the
high-power PA setting is expensive. **0 dBm is the efficient point**: power is better saved with the interval than
with the TX power.

## Full-firmware check

`ble_sensor LOG=0 ADV_MS=1000 SENSOR_S=10 TX_DBM=0`, the firmware as it would ship. 10 mA range.

| Mean | σ | n | σ_mean | Max |
|---|---|---|---|---|
| **16.1 µA** | 29.5 µA | 1300 (≈ 10 min) | 0.8 µA | 131.8 µA |

The model from the parts measured above:

```
0.366 µA + 12.63 µC / 1.005 s + 9.56 µC / 10 s = 0.37 + 12.57 + 0.96 = 13.9 µA
```

The measured value is 2.2 ± 0.8 µA higher. The current sensor task also wakes once a second, 9 times per 10 s, to
check that the payload reload went through. At about **2.4 µC per bare wake-up** that accounts for the difference.
The model holds, and the check costs about 14 % of the total for nothing. Removing it, and using the DRDY interrupt
for the sensor, gives 0.37 + 12.57 + 0.37 = **13.3 µA** at the same settings.

Since 2026-10-30 the sensor task wakes once a second only until the reload has gone through, then sleeps for the rest
of the period (`ble_sensor/app_main.c`). Not verified yet: the only run with it is the unresolved 6.55 µA below.

## RF CW no-pi board (2026-10-30)

The board used for the conducted comparison with BSN-N54 #2: no U2, PA-side pi network removed (see the
[rework log](../../README.md#rework-log)), HDC2010, I2C pull-ups and C5 fitted, **J1 terminated with a 50 Ω
broadband load** like N54 #2. Meter: Keysight 34465A (the reference meter for the N54 set of the same day). 3.0 V
at TP9 (the J-Link reported VTref 2.35 V while flashing, with the meter bypassed; not explained).

| # | Build | Range | V | Mean | σ | n | Result |
|---|---|---|---|---|---|---|---|
| N1 | `ble_sensor LOG=0 ADV_MS=5000 SENSOR_S=10` | 10 mA, NPLC 100, autozero off | 3.0 | **6.55 µA** | | ≈ 200 | model 3.85 µA, **+2.7 µA unexplained** |
| N2 | `ble_sensor LOG=0 ADV_MS=50 SENSOR_S=0` | 10 mA | 3.0 | 224 µA | 42 µA | 200 | Q_adv = **12.30 ± 0.16 µC** |
| N3 | same | 10 mA | 2.0 | 315 µA | 75 µA | 200 | Q_adv = **17.30 ± 0.29 µC** |

N2/N3 use board #1's floor (0.366 µA); this board's own floor is not measured yet.

- **The advertising charge matches board #1** (12.63 / 16.92 µC): without the pi network and into 50 Ω the C23 needs
  the same charge per advert. The adverts don't explain N1.
- **N1:** the model is 0.366 + 12.63 / 5.005 + 9.56 / 10 = 3.85 µA. Checked and ruled out: debug state (J-Link
  unplugged, TP9 shorted before power-on), supply (3.0 V at TP9), C5 (fitted), missing sensor or pull-ups (fitted).
  Left:
  - **This board's floor.** Not measured; it would have to be about 3 µA.
  - **The reload retries.** If the payload reload never succeeds, the sensor task falls back to waking every second,
    as before the fix: 9 × 2.4 µC / 10 s = +2.2 µA, which gives about 6.0 µA, close to N1.

  Next: `pwrtest standby` on this board (floor), then `ble_sensor LOG=1` on the UART to see whether
  `prepareLoad`/`loadByHandle` fail at a 5 s interval.

## Pitfalls

Found during these measurements. Each one gave a plausible but wrong current.

| Symptom | Cause | Fix |
|---|---|---|
| 44 µA floor | SHTC3 (U2) idle after power-on | `Shtc3_sleep()` at boot (`pwrtest`, `ble_sensor`) |
| Floor 0.925 µA instead of 0.366 µA | Debug state not cleared after flashing: PSU off/on was not a full power-on reset | Unplug the J-Link, short TP9 to TP10 before power-on |
| 2.3 mA, CPU stuck in the boot ROM, RAM not initialised | Same, straight after `jflash` | Same |
| 2.3 mA with the firmware sitting in `Power_sleep()` | Rising-edge interrupt trigger on DIO21 (HDC INT) set in SysConfig | Set the trigger at runtime, only in the mode that uses it |
| 1.3 mA in `sensor` mode at 1 s | `usleep(1000000)` is invalid in POSIX (it must be below 1 000 000) and returns at once: the loop ran at 333 Hz | `sleepMs()` splits it into `sleep()` + `usleep()`. All other `usleep()` calls in the firmware are below 1 s. |
| BTHome battery 54 %, VDDS 2.64 V at 3.0 V supply | Boot-time reading while C5 charged through the meter's µA shunt | Power on with the meter on 10 mA or bypassed |
| No SWD connection | Meter on a µA range: its shunt starves the board when the debugger wakes it | Meter on 10 mA or bypassed while flashing |
| Low or noisy event charge | Too few events per meter reading | Run events at 5–20 Hz |

## Still to measure

For the battery-life model (0 dBm, advertising every 5 s or slower, timer or DRDY sensor wake, room temperature):

- [ ] **The 6.55 µA full-firmware result on the no-pi board** (see above): its floor (`pwrtest standby`), then the
      reload with `LOG=1`.
- [ ] Full-firmware check at 5 s advertising on board #1 (model 3.85 µA).
- [ ] Floor against supply voltage (`pwrtest standby` at 2.4 and 2.0 V). Until measured, assume constant power like
      the N54 (+35 % at 2.0 V).
- [ ] Sensor readings at 2.0 V (`pwrtest sensor`, `sensor_irq`). Until measured, assume the advertising scaling.
- [x] The same set on BSN-N54 (2026-10-27/30, see [`hardware/N54/testing/Power`](../../../N54/testing/Power/POWER_MEASUREMENTS.md)).

Later or out of scope for the model:

- [ ] Real CR2032: VDD dip during TX (sets the end-of-life voltage; on rev B).
- [ ] Scope and shunt: pulse shape and peak current per advert (CR2032 peak derating), and the phases of an event.
- [ ] Re-measure the floors with U2 removed and the board cleaned.
- [ ] Shutdown floor with a retained reset-reason and "refused" counter, and the BLE stack start-up charge. Not
      needed for the MCU choice: shutdown saves at most about 0.2 µA, less than a cold boot costs at any interval
      up to about 60 s.

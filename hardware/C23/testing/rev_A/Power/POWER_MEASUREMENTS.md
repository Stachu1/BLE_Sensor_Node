# BSN-C23-A current measurements

Average-current measurements on board #1 (2026-10-26), for the battery-life model, the comparison with the N54
variant and the settings trade-offs:

```
I_avg = I_floor + Q_adv / T_adv + (Q_sensor + Q_reload) / T_sensor
```

Each `Q` is the charge of one event above the floor. It is measured as an average current at a known, fast event
rate, so a slow, precise ammeter is enough: `Q = (I_avg − I_floor) × T_event`. `Q_reload` is the cost of loading a
new reading into the running advertising set (found on 2026-11-10, see [Payload reload](#payload-reload-2026-11-10)).

Raw summary of every reading: [`power_2026-10-26.csv`](power_2026-10-26.csv) and
[`power_2026-11-10.csv`](power_2026-11-10.csv).

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
| **Payload reload** (prepare/load on the running advertising set), 2026-11-10 | **20.6 ± 0.4 µC** (19.3 ± 0.7 µC on the no-pi board) | `ble_sensor SENSOR_S=1` |
| **One advert per DRDY** (DRDY wake, reading, load, one advertising event), 2026-11-10 | **25.1 ± 2.0 µC** | `ble_sensor DRDY=7` |
| Sleep floor at 2.4 / 2.0 V, relative to 3.0 V, 2026-11-10 | +11 / +20 % (board #1), +12 / +29 % (no-pi board) | `pwrtest standby` |
| Sensor reading at 2.0 V, relative to 3.0 V, 2026-11-10 (no-pi board) | +25 % (DRDY, 4.68 µC), +26 % (timer) | `pwrtest sensor_irq`, `sensor` |
| Bare timer wake-up from standby | withdrawn (was ≈ 2.4 µC, see [Full-firmware check](#full-firmware-check)) | |
| Shutdown floor | **unresolved** (0.42 and 0.9 µA) | `pwrtest shutdown` |
| SHTC3 (U2) left idle after power-on | +43 µA (fixed in firmware) | |
| **Full firmware**: 1 s advertising, sensor every 10 s, 0 dBm | **16.1 ± 0.8 µA** (model with the reload: 15.9 µA) | `ble_sensor` |
| **Full firmware**: 5 s advertising, sensor every 10 s, no-pi board, 2026-11-10 | **6.5 ± 0.4 µA** (model with the reload: 6.1 µA) | `ble_sensor ADV_MS=5000` |
| **One advert per DRDY**, every 5.07 s, 2026-11-10 | **5.8 ± 0.6 µA** board #1, 5.4 ± 0.4 µA no-pi (model from the event charge: 5.3 µA) | `ble_sensor DRDY=4` |

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
polling period is 97 ms rather than 100 ms so it cannot lock to the meter's sample clock. Advertising is already
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
  RAM is lost in shutdown, so the rate could not be read back. It is the same HDC2010 clock as R3.

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

The measured value is 2.2 ± 0.8 µA higher. On 2026-10-26 this was put down to the sensor task waking once a second
to check the reload, at about 2.4 µC per bare wake-up. That 2.4 µC was derived from this same difference, not
measured. **On 2026-11-10 the payload reload itself was measured at 20.6 µC** (see
[Payload reload](#payload-reload-2026-11-10)). With it the model is

```
0.37 + 12.57 + (9.56 + 20.6) µC / 10 s = 15.9 µA
```

which matches 16.1 ± 0.8 µA without any cost for the wake-ups. The 2.4 µC per bare wake-up is withdrawn.

Since 2026-10-30 the sensor task wakes once a second only until the reload has gone through, then sleeps for the rest
of the period (`ble_sensor/app_main.c`).

## RF CW no-pi board (2026-10-30)

The board used for the conducted comparison with BSN-N54 #2: no U2, PA-side pi network removed (see the
[rework log](../../../README.md#rework-log)), HDC2010, I2C pull-ups and C5 fitted, **J1 terminated with a 50 Ω
broadband load** like N54 #2. Meter: Keysight 34465A (the reference meter for the N54 set of the same day). 3.0 V
at TP9 (the J-Link reported VTref 2.35 V while flashing, with the meter bypassed. On 2026-11-10 the same low VTref
went away once the J-Link GND and VTref were on the right rev A pins, see [Pitfalls](#pitfalls). Likely the same
cause here.)

| # | Build | Range | V | Mean | σ | n | Result |
|---|---|---|---|---|---|---|---|
| N1 | `ble_sensor LOG=0 ADV_MS=5000 SENSOR_S=10` | 10 mA, NPLC 100, autozero off | 3.0 | **6.55 µA** | | ≈ 200 | model 3.85 µA, **+2.7 µA, explained on 2026-11-10 by the reload** |
| N2 | `ble_sensor LOG=0 ADV_MS=50 SENSOR_S=0` | 10 mA | 3.0 | 224 µA | 42 µA | 200 | Q_adv = **12.30 ± 0.16 µC** |
| N3 | same | 10 mA | 2.0 | 315 µA | 75 µA | 200 | Q_adv = **17.30 ± 0.29 µC** |

N2/N3 use board #1's floor (0.366 µA). This board's own floor, measured on 2026-11-10, is 0.70 µA, which moves Q_adv
by less than 0.02 µC.

- **The advertising charge matches board #1** (12.63 / 16.92 µC): without the pi network and into 50 Ω the C23 needs
  the same charge per advert. The adverts don't explain N1.
- **N1:** the model is 0.366 + 12.63 / 5.005 + 9.56 / 10 = 3.85 µA. Checked and ruled out: debug state (J-Link
  unplugged, TP9 shorted before power-on), supply (3.0 V at TP9), C5 (fitted), missing sensor or pull-ups (fitted).
  The two suspects at the time were this board's floor and the reload retries.
- **Resolved on 2026-11-10:** the floor is 0.70 µA, and N1 repeats (6.5 µA). The cause is the cost of each payload
  reload, about 20 µC, see [Payload reload](#payload-reload-2026-11-10).

### Home check of the floors (2026-10-31, indicative only)

Taken at home with a UNI-T UT139S on the µA range, which shows no mean. The values are where the display settled,
±0.2–0.3 µA at best. Supply: 3.3 V LDO. Every board got the J-Link unplugged and TP9 shorted before power-on.

| Board | Fitted | Build | Floor (display) |
|---|---|---|---|
| #1 | U2, U3, C5 | `pwrtest standby` | ≈ 0.75 µA (≈ 2 µA for the first few seconds) |
| no sensors | no U2, no U3, no C5 | `pwrtest standby SHTC3_SLEEP=0` | ≈ 1.1 µA |
| no-pi (likely the N1 board) | U3, C5, no U2 | `pwrtest standby SHTC3_SLEEP=0` | ≈ 0.5–0.6 µA |

- **No board has a floor anywhere near the ~3 µA that N1 would need.** The floor is ruled out as the cause of the
  6.55 µA. The absolute floors still need the Keysight.
- On the board without sensors, the default `pwrtest standby` read about 250 µA, jumping around. Its boot-time I2C
  write to the SHTC3 never completes without the sensors (and pull-ups), which keeps the device out of standby
  (it was awake enough to flash at the first attempt). `SHTC3_SLEEP=0` skips the I2C traffic.
- The board without sensors reads highest, but it also has no C5, so the meter sees the bare recharge pulses.
  This is not taken as a real difference.
- `ble_sensor LOG=0 ADV_MS=5000 SENSOR_S=10` on board #1 with `tools/bsn_scan.py`: the BTHome packet ID advanced
  about every 10 s, so the reload went through on that board. Windows only reported about one advert a minute,
  too few to look for extra adverts between the 5 s ones. Not yet repeated on the no-pi board.
- **Second suspect:** `GapAdv_prepareLoadByHandle`/`loadByHandle` may disable and re-enable advertising on every
  reload. Confirmed on 2026-11-10, see [Payload reload](#payload-reload-2026-11-10).

## Payload reload (2026-11-10)

Repeat of N1 on the no-pi board and the follow-up on both boards. Meter: Keysight 34460A, NPLC 100 (about 2 s per
sample), 10 mA range unless noted. 3.0 V at TP9. Builds from the tag `fw/BSN-C23-A`, plus the `DRDY` option of the
`ble_sensor` makefile on main (the same code on both revisions). Floors used: 0.70 µA on the no-pi board (P1 below),
0.366 µA on board #1 (F4).

| # | Board | Build | Mean | σ | n | Model without reload | Result |
|---|---|---|---|---|---|---|---|
| P1 | no-pi | `pwrtest standby SHTC3_SLEEP=0`, µA range | 0.698 µA | 0.051 µA | 100 | | floor 0.70 µA |
| P2 | no-pi | `ble_sensor ADV_MS=50 SENSOR_S=0` | 229 µA | 13.3 µA | 125 | | Q_adv = 12.56 ± 0.07 µC |
| P3 | no-pi | `ble_sensor ADV_MS=5000 SENSOR_S=0` | 3.16 µA | 2.99 µA | 550 | 3.21 µA | adverts alone match |
| P4 | no-pi | `ble_sensor ADV_MS=5000 SENSOR_S=10` | **6.5 µA** | 5.6 µA | 170 | 4.16 µA | N1 repeats |
| P5 | no-pi | `ble_sensor ADV_MS=5000 SENSOR_S=1` | 32 µA | 6.5 µA | 100 | 12.7 µA | **Q_reload = 19.3 ± 0.7 µC** |
| P6 | #1 | `ble_sensor ADV_MS=5000 SENSOR_S=1` | 32.9 µA | 5.1 µA | 200 | 12.4 µA | **Q_reload = 20.6 ± 0.4 µC** |

`SENSOR_S=1` reads the sensor and reloads the payload once a second. The model without the reload is floor +
12.6 µC / 5.005 s + 9.56 µC / 1.004 s. Everything above it is the reload.

- **Each payload reload costs about 20 µC**, 1.6 times an advert. It is the same on both boards, with and without the
  pi network and antenna.
- **It explains N1 and P4.** With the reload the model is 0.70 + 2.51 + (9.56 + 19.3) / 10 = 6.1 µA, against 6.5 ± 0.4
  and 6.55 µA measured.
- **Why:** the SDK header (`gap_advertiser.h`) states that `GapAdv_prepareLoadByHandle` disables advertising on the
  set and `GapAdv_loadByHandle` re-enables it. How the 20 µC splits between an extra advert at the re-enable and the
  stack work was not measured.
- **The reload went through at 5 s on board #1** (packet ID advancing, home check). On the no-pi board the scanner
  can't see the adverts (50 Ω load), so failed reloads there are not ruled out. The cost per reload is the same on
  both boards.
- **The N54 has no such cost:** its full firmware matches its model without a reload term (6.1 against 6.01 µA).
  Zephyr's `bt_le_adv_update_data` swaps the data without stopping advertising.

### One advert per DRDY

`ble_sensor DRDY=<rate>`: advertising is off between events. The HDC2010 runs in auto mode, each DRDY wakes the
sensor task, which reads the result and VDDS, loads the payload and enables advertising for one event
(`GAP_ADV_ENABLE_OPTIONS_USE_MAX_EVENTS`, 1). No periodic advertising and no reload of a running set. The HDC2010
period is taken as 1.4 % slow, as measured on board #1 (R3): 5.07 s at `DRDY=4`, 0.2027 s at `DRDY=7`.

| # | Board | Build | Mean | σ | n | Result |
|---|---|---|---|---|---|---|
| D1 | #1 | `DRDY=7` (5 events/s) | 124 µA | 105 µA | 115 | **Q_event = 25.1 ± 2.0 µC** |
| D2 | #1 | `DRDY=4` (every 5.07 s) | **5.8 µA** | 5.6 µA | 100 | model from D1: 0.37 + 25.1 / 5.07 = 5.3 µA |
| D3 | no-pi | `DRDY=4` | **5.4 µA** | 5.4 µA | 200 | model from D1 with this floor: 5.7 µA |

- **The model holds with the measured event charge.** D2 and D3 agree with the prediction within 1σ.
- **The event costs about 9 µC more than its parts** (12.63 µC advert + 3.72 µC DRDY reading = 16.4 µC). Likely the
  host enabling advertising and handling its end for a single event, which periodic advertising doesn't repeat. Not
  measured separately.
- **The σ of D1 is large** for 10 events per sample. Not looked into. More samples would tighten Q_event.
- `tools/bsn_scan.py` on board #1 with `DRDY=4`: packet 67 to 86 in 96 s, 5.05 s per reading, matching the HDC2010
  period. Valid readings, VDD 3.00 V. So it sends one advert per reading as intended.

### Floor against supply voltage

`pwrtest standby` (board #1) and `pwrtest standby SHTC3_SLEEP=0` (no-pi board), µA range, TP9 shorted before each
power-on.

| V | Board #1 | n | No-pi board | n | Difference |
|---|---|---|---|---|---|
| 3.0 | 0.941 ± 0.006 µA | 60 | 0.703 µA (σ 0.048 µA) | — | 0.24 µA |
| 2.4 | 1.040 ± 0.008 µA (+11 %) | 80 | 0.788 ± 0.012 µA (+12 %) | 75 | 0.25 µA |
| 2.0 | 1.132 ± 0.008 µA (+20 %) | 155 | 0.910 ± 0.012 µA (+29 %) | 50 | 0.22 µA |

- **The floor rises by 11–12 % at 2.4 V and 20–29 % at 2.0 V**, less than the +35 % assumed from the N54.
- **Board #1 reads 0.94 µA, against 0.366 µA (F4) on 2026-10-26** with the same build and procedure. A repeat with
  the J-Link fully removed gave the same. The cause is not known. Board #1 has visible flux residue.
- **The difference between the boards is flat with voltage** (0.22–0.25 µA). Candidates: the SHTC3 asleep (only on
  board #1), or a leak on a regulated node such as the DC/DC output, which would not scale with the supply either.
  A cleaning test (IPA around U1 and the DC/DC inductor), then lifting U2, would separate them.

### Sensor readings against supply voltage

No-pi board, 1 mA range, floors from the table above (0.703 µA at 3.0 V, 0.910 µA at 2.0 V). The reading periods are
taken from board #1 (R2, R3), same builds: 101.0 ms for `sensor`, 202.7 ms for `sensor_irq`. Not counted on this
board.

| # | Build | V | Mean | σ | n | Charge per reading | Board #1 (R2, R3) |
|---|---|---|---|---|---|---|---|
| S1 | `pwrtest sensor PERIOD_MS=97` | 3.0 | 68.7 µA | 0.68 µA | 50 | 6.87 ± 0.01 µC | 9.56 µC |
| S2 | same | 2.0 | 86.7 µA | 2.0 µA | 50 | 8.66 ± 0.03 µC (+26 %) | |
| S3 | `pwrtest sensor_irq HDC_AMM=7` | 3.0 | 19.2 µA | 2.4 µA | 65 | **3.75 ± 0.06 µC** | 3.72 µC |
| S4 | same | 2.0 | 24.0 µA | 1.4 µA | 50 | **4.68 ± 0.04 µC (+25 %)** | |

- **A sensor reading costs about 25 % more at 2.0 V** than at 3.0 V, with either wake-up. The adverts rise by 34 %.
- **The DRDY reading matches board #1** (3.75 against 3.72 µC).
- **The polled reading does not:** 6.87 µC here against 9.56 µC on board #1, same build. Not explained. The period
  was not counted on this board, and board #1 was not repeated today.

## Average current against advertising interval (model)

The charges above put into the model, at 0 dBm and 3.0 V, board #1 (floor 0.366 µA from 2026-10-26). Updated on
2026-11-10 with the payload reload (Q_reload = 20.6 µC) and the one-advert-per-DRDY event (Q_event = 25.1 µC).
Four ways of running the node:

```
Periodic (1, 2):        I_avg = 0.366 µA + 12.63 µC / (T + 5 ms) + (Q_sensor + 20.6 µC) / T_sensor
One advert per DRDY (3): I_avg = 0.366 µA + 25.1 µC / T
Shutdown (4):           I_avg = 0.215 µA + (15.2 µC + Q_BLE + 12.63 µC) / T
```

1. **Periodic advertising, DRDY wake:** HDC2010 auto mode, DRDY wakes the MCU from standby (Q_sensor = 3.72 µC), and
   each reading is reloaded into the running advertising set.
2. **Periodic advertising, timer wake:** as the current `ble_sensor` (Q_sensor = 9.56 µC), reload every reading.
3. **One advert per DRDY:** `ble_sensor DRDY=…`. Advertising off between events, reading period = advertising
   period. Measured as a whole event (D1).
4. **Shutdown, DRDY wake:** every DRDY is a cold boot, a reading, a BLE stack start and one advert, then shutdown
   again. Reading period = advertising period.

| Advertising interval T | 1 s | 5 s | 10 s | 60 s | 120 s |
|---|---|---|---|---|---|
| 1. Periodic, DRDY, reading every advert | 37.3 | 7.75 | 4.06 | 0.98 | 0.67 |
| 1. Periodic, DRDY, reading every 60 s | 13.3 | **3.29** | 2.03 | 0.98 | 0.88 |
| 2. Periodic, timer, reading every 10 s (current `ble_sensor`) | 15.9 | 5.91 | 4.64 | 3.59 | 3.49 |
| 3. One advert per DRDY | 25.5 | 5.39 | **2.88** | **0.78** | **0.58** |
| 4. Shutdown, DRDY (Q_BLE 10–40 µC) | 48 (38–68) | 9.8 (7.8–13.8) | 5.0 (4.0–7.0) | 1.01 (0.85–1.35) | 0.61 (0.53–0.78) |

All values in µA.

- **The reload sets the design.** A reload costs 1.6 adverts, so reading and reloading often is expensive. At 5 s
  the cheapest option is periodic advertising with a slow reading (every 60 s): 3.29 µA.
- **From about 10 s up, one advert per DRDY is the best option**, with a fresh reading in every advert. At 120 s it
  also beats shutdown.
- **The current `ble_sensor` (row 2) is the worst standby option at 5 s and slower**, because it reloads every 10 s.
- **Validity:** row 2 matches the 1 s full-firmware check (15.9 against 16.1 ± 0.8 µA) and the 5 s runs on the no-pi
  board with its own floor (6.1 against 6.5 and 6.55 µA). Row 3 matches D2 and D3 within 1σ.
- **Not tested:** writing the new reading into the advertising buffer in place, without prepare/load. The stack
  transmits straight from that buffer, so it might avoid Q_reload. TI documents only the prepare/load route, and a
  write during an advertising event could send a mixed packet.
- **Inputs that are not measured:**
  - Shutdown floor: the datasheet value (165 nA CC2340R5 + 50 nA HDC2010 = 0.215 µA), since the measured one is
    unresolved.
  - BLE stack start after a cold boot (Q_BLE): estimated at 20 µC (10–40), about 5–15 ms of stack init at about
    2.5 mA.
- **Shutdown sends one advert per wake.** A scanner can miss one, so a real node would send 2–3, adding 12.6 µC
  each. The same applies to row 3.
- **Board #1's floor read 0.94 µA on 2026-11-10**, not 0.366 µA (see [Floor against supply
  voltage](#floor-against-supply-voltage)). With 0.94 µA every row moves up by 0.57 µA.
- An interactive version with the N54 for comparison and the 2.4 / 2.0 V cases was made on 2026-10-30, before the
  reload was known. Redo this table with the rev B numbers for the final results.

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
| Full firmware 2.7 µA above the model | Each payload reload costs about 20 µC (prepare/load disables and re-enables advertising) | `Q_reload` term in the model, or one advert per DRDY |
| J-Link "No CFG-AP detected" on every try, VTref 0.77 V below the supply | Wired to the rev B test points (README on main) and J-Link pin 2 taken for GND (it is NC) | Rev A: SWDIO TP3, SWCLK TP5, nRESET TP4, VTref TP9, GND TP10, J-Link GND on pin 4 |

## Still to measure

For the battery-life model (0 dBm, advertising every 5 s or slower, timer or DRDY sensor wake, room temperature):

- [x] **The 6.55 µA full-firmware result on the no-pi board.** Repeats (6.5 µA), explained by the payload reload
      (2026-11-10).
- [x] Full-firmware check at 5 s. Replaced by the one-advert-per-DRDY check on board #1 (5.8 µA, model 5.3 µA) and
      the reload measured on both boards (2026-11-10).
- [x] Floor against supply voltage: +11–12 % at 2.4 V, +20–29 % at 2.0 V (2026-11-10).
- [x] Sensor readings at 2.0 V: +25 % (DRDY) and +26 % (timer) on the no-pi board (2026-11-10).
- [ ] Polled reading on the no-pi board (6.87 µC) against board #1 (9.56 µC). Count the period, repeat on board #1.
- [x] The same set on BSN-N54 (2026-10-27/30, see [`hardware/N54/testing/Power`](../../../../N54/testing/Power/POWER_MEASUREMENTS.md)).

Later or out of scope for the model:

- [ ] Real CR2032: VDD dip during TX (sets the end-of-life voltage, on rev B).
- [ ] Scope and shunt: pulse shape and peak current per advert (CR2032 peak derating), and the phases of an event.
- [ ] Re-measure the floors with U2 removed and the board cleaned. Now also to explain board #1's 0.94 µA
      (0.366 µA on 2026-10-26).
- [ ] Shutdown floor with a retained reset-reason and "refused" counter, and the BLE stack start-up charge. Not
      needed for the MCU choice: shutdown saves at most about 0.2 µA, less than a cold boot costs at any interval
      up to about 60 s.

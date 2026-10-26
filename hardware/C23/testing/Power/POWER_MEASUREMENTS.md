# BSN-C23-A current measurements

Average-current measurements on board #1 with the `pwrtest` firmware (`firmware/C23/pwrtest`), which holds the
board in one fixed power state per build, with no BLE stack and no UART. The results feed the battery-life model
and the comparison with the N54 variant:

```
I_avg = I_floor + Q_adv / T_adv + Q_sensor / T_sensor
```

Each `Q` is the charge of one event above the floor. It is measured as an average current at a known event
rate, so a slow, precise ammeter is enough: `Q = (I_avg − I_floor) × T_event`.

Raw summary: [`power_2026-10-26.csv`](power_2026-10-26.csv).

**Results so far (2026-10-26, 3.0 V):**

| Quantity | Value |
|---|---|
| Standby floor (MCU standby, RTC on LFOSC, both sensors asleep) | **0.925 µA** |
| Shutdown floor (board baseline) | **0.420 µA** |
| Sensor reading, MCU timer + 2 ms wait (as in `ble_sensor`) | **9.50 µC** |
| Sensor reading, HDC2010 auto mode, DRDY wakes the MCU from standby | **3.60 µC** |
| Sensor reading, HDC2010 auto mode, DRDY wakes the MCU from shutdown (full reboot) | **15.3 µC** |
| SHTC3 (U2) left idle after power-on | **+43 µA** (fixed in firmware) |

## Setup

- **Board:** BSN-C23-A #1. Still has the TI reference RF values. **U2 (SHTC3) is fitted** on this board,
  although the BOM marks it DNP.
- **Supply:** 3.0 V bench PSU on TP9/TP10, no coin cell.
- **Meter:** Keysight 34461A in series, DC current, 500 samples per point (800 for `shutdown_wake`), mean and
  standard deviation from its statistics. About 150 samples per minute. Range as noted per measurement,
  fixed (not autorange).
- **Procedure for each build:**
  1. Bypass the meter and connect the J-Link.
  2. `make jflash MODE=...`.
  3. Unplug **all** J-Link wires.
  4. Power off and check that TP9 reaches 0 V (short TP9 to TP10 if not).
  5. Power on and wait about 10 s (every build waits 5 s after boot).
  6. Remove the bypass and measure.

  After `jflash` the CC2340 waits in the ROM (SACI) until a real power-on reset, drawing a few mA, so the power
  cycle is not optional (see [Pitfalls](#pitfalls)).
- **Event rates** were measured, not assumed. `sensorEvents` was read twice, 30 s apart, over the J-Link
  without halting (`mem32`).

### Why the event modes run fast

The 34461A integrates each reading over a short window. One event per second is a pulse of a few ms that most
readings miss and a few catch in full. In the first `sensor` attempt (1 s period) that gave σ = 112 µA on a
mean of 7.7 µA, an uncertainty of ±5 µA on the mean, which is unusable. Running the events at 5–10 Hz puts
several events in every reading. The charge per event stays the same as long as the MCU still reaches its
sleep state between events, which it does with more than 90 ms to spare. The polling period is 97 ms rather
than 100 ms so it cannot lock to the meter's sample clock.

## Measurements

σ_mean = σ / √n. Floors: standby 0.925 µA for the standby-based modes, shutdown 0.420 µA for `shutdown_wake`.

| # | Build | State | Range | Mean | σ | σ_mean | Event period | Charge per event |
|---|---|---|---|---|---|---|---|---|
| 1 | `standby SHTC3_SLEEP=0` (equivalent) | Standby, SHTC3 left idle | µA | 44 µA | — | — | — | — |
| 2 | `standby` | Standby, both sensors asleep | µA | **0.925 µA** | 0.293 µA | 0.013 µA | — | — |
| 3 | `shutdown` | Shutdown, both sensors asleep | µA | **0.420 µA** | 0.052 µA | 0.002 µA | — | — |
| 4 | `sensor PERIOD_MS=1000` | Timer polling, 1 s | 1 mA | 7.7 µA | 112 µA | 5.0 µA | 1.0 s | 6.8 ± 5 µC (superseded by #5) |
| 5 | `sensor PERIOD_MS=97` | Timer polling | 1 mA | **95.0 µA** | 0.8 µA | 0.04 µA | 101.0 ms (297 in 30 s) | **9.50 ± 0.04 µC** |
| 6 | `sensor_irq HDC_AMM=7` | HDC2010 auto 0.2 s, DRDY wake from standby | 1 mA | **18.7 µA** | 15.8 µA | 0.71 µA | 202.7 ms (148 in 30 s) | **3.60 ± 0.15 µC** |
| 7 | `shutdown_wake HDC_AMM=7` | HDC2010 auto 0.2 s, DRDY wake from shutdown | 10 mA | **76 µA** | 72 µA | 2.5 µA | 202.7 ms (same sensor clock as #6) | **15.3 ± 0.5 µC** |

Notes:

- **#1** is the state every board was in before the fix. After power-on the SHTC3 idles at 45 µA (typical)
  until it is sent its Sleep command (0xB098), and no firmware sent it because U2 is DNP on rev A. Only one
  reading was taken. `Shtc3_sleep()` is now called at boot in `pwrtest` and `ble_sensor`, and a board without U2
  just NACKs it.
- **#2 and #3** fluctuate between about 0.4 and 1.1 µA (standby) because the CC2340 wakes briefly for regulator
  recharge and RC-oscillator calibration. The mean over 500 samples is the number to use.
- **#5:** each event takes about 4 ms on top of the 97 ms sleep (101.0 ms measured). Per event: VDDS read, HDC2010
  trigger over I2C, 2 ms `usleep`, result read. That is two standby entries and exits per event.
- **#6:** no trigger write, no 2 ms wait and no VDDS read, and one standby cycle per event. The HDC2010's own
  oscillator runs 1.4 % slow (202.7 ms instead of 200 ms). Readings were valid (22.7 °C, 43.0 %RH, no I2C errors).
- **#7:** every event is a full cold boot (ROM, C startup, FreeRTOS, GPIO/I2C init), then the read and shutdown.
  The 1 mA range overloaded on the boot peaks, so the 10 mA range was used. RAM is lost in shutdown, so the
  event rate could not be read back. It is the same HDC2010 clock as #6.

## What the floor is made of

Typical datasheet values compared with the measurements:

| | Standby | Shutdown |
|---|---|---|
| Measured | 0.925 µA | 0.420 µA |
| CC2340R5 (datasheet) | 0.71 µA | 0.15 µA |
| HDC2010 sleep + SHTC3 sleep (datasheet) | 0.05 + 0.3 µA | 0.05 + 0.3 µA |
| Left over (flux, other leakage) | ≈ 0 | ≈ 0 |

- **The MCU's share of standby** is 0.925 − 0.420 = **0.505 µA**. The datasheet difference is 0.56 µA, so they
  agree.
- **Leakage:** the SHTC3 alone explains most of the shutdown floor, so leakage from flux residue is small.
- **To do:** re-measure #2 and #3 with U2 removed and the board cleaned. Expect about 0.6 µA standby and about
  0.2 µA shutdown. Use the shutdown value as the board baseline to offset other boards and setups.

## Sensor readings: comparison

| Method | Floor | Charge per reading | Added current at 10 s | at 60 s |
|---|---|---|---|---|
| Timer polling (current `ble_sensor`) | 0.925 µA | 9.50 µC | 0.95 µA | 0.16 µA |
| DRDY wake from standby | 0.925 µA | 3.60 µC | 0.36 µA | 0.06 µA |
| DRDY wake from shutdown | 0.420 µA | 15.3 µC | 1.53 µA | 0.26 µA |

- **Polling vs DRDY wake:** the interrupt saves 62 % per reading. Polling costs more than the wait itself would
  suggest, because each standby entry and exit costs charge. In the stuck loop in [Pitfalls](#pitfalls), one
  back-to-back read without standby cost about 3.9 µC (1.3 mA / 333 per second), while one polled read with
  standby costs 9.5 µC.
- **Standby vs shutdown:** shutdown saves 0.505 µA all the time but costs 11.7 µC more per wake. The break-even
  is 11.7 µC / 0.505 µA ≈ **23 s**. This is for sensor-only wakes. A real node waking from shutdown would also
  have to start the BLE stack and advertise on every wake, which moves the break-even out further. Measure the
  stack start-up cost before deciding.
- **For the HDC2010 thresholds:** in auto mode the HDC2010 can also interrupt only when temperature or humidity
  crosses a threshold, so the MCU would only wake on a change. Not measured yet.

## Pitfalls

Found during these measurements. Each one gave a plausible but wrong current.

| Symptom | Cause | Fix |
|---|---|---|
| 44 µA floor | SHTC3 (U2) idle after power-on | `Shtc3_sleep()` at boot |
| 1.3 mA steady in `sensor` mode at 1 s | `usleep(1000000)` is invalid in POSIX (it must be below 1 000 000) and returns at once, so the loop ran at 333 Hz | `sleepMs()` splits it into `sleep()` + `usleep()`. All other `usleep()` calls in the firmware are below 1 s. |
| 2.3 mA steady after flashing `sensor_irq` | The CPU was in the boot ROM (PC 0x0F00_24xx, RAM never initialised): the power cycle after `jflash` was not a full power-on reset | Unplug all J-Link wires, check that TP9 reaches 0 V |
| (would have been a wrong `sensor_irq` result) | The HDC INT pin had no interrupt edge in `pwrtest.syscfg` | `interruptTrigger = "Rising Edge"` |
| No SWD connection with the meter in series | The meter's µA-range shunt starves the board when the debugger wakes it | Bypass the meter while flashing |

## Still to measure

- [ ] `idle` and `active` reference points.
- [ ] Advertising: `ble_sensor` at two advertising intervals gives `I_floor` with the stack running and
      `Q_adv`. Then repeat at −8, 0, +4 and +8 dBm.
- [ ] BLE stack start-up charge, for the shutdown-wake architecture.
- [ ] Pulse shape and peak current on a scope with a shunt resistor (peak current for the CR2032, and the duration
      of each phase).
- [ ] Supply sweep 3.0, 2.7, 2.4, 2.1 V for the standby floor and `Q_adv`.
- [ ] Real CR2032: VDD dip during TX.
- [ ] Re-measure the floors with U2 removed and the board cleaned.
- [ ] The same set on BSN-N54.

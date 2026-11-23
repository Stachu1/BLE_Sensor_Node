# BSN-N52 firmware

Firmware for `BSN-N52-A` (nRF52805), moved here from the separate AirTag project on 2026-11-23. The names were
changed to this repo's scheme: board `bsn_n52/nrf52805` (was `airtag/nrf52805`), advertised name `BSN-N52` (was
`BSN-52`), hwtest name `BSN-N52-HWTEST` (was `AirTag-HWTEST`). Boards flashed before the move still advertise the
old names until they are reflashed.

nRF Connect SDK v3.4.0 (Zephyr 4.4), custom board `bsn_n52/nrf52805` in `boards/oj/bsn_n52`.

Pins (from `hardware/N52/BSN-N52.kicad_sch`): P0.16 SCL, P0.18 SDA, P0.12 HDC2010 INT, P0.21 reset (J1). No external I2C
pull-ups (nRF internal ones are used), no LED, no UART, no 32 kHz crystal (LFCLK = RC).

Board status, MACs, tool usage and pitfalls: [BRINGUP.md](BRINGUP.md).

## Build
```
.\build.ps1 hwtest            # -> hwtest\build\zephyr\zephyr.hex
.\build.ps1 hwtest -Carrier   # ends in a continuous RF carrier (2440.25 MHz) instead of BLE advertising
.\build.ps1 hwtest -SkipDcdc  # skip the DC/DC test if the board boot-loops in it
```

## hwtest
J-Link (tested) or ST-Link (`--probe stlink`, pyocd, untested), see BRINGUP.md:
```
python hwtest\scripts\hwtest.py soc      # does the SoC answer on SWD (DAP, FICR, UICR)
python hwtest\scripts\hwtest.py run      # flash + run + print the report
python hwtest\scripts\hwtest.py report   # just read the report from RAM
```
Report channels: RAM struct `hwtest_report` (what the script reads), RTT console (`printk`, repeats every 5 s),
BLE advertisement `BSN-N52-HWTEST` (manufacturer data: `HW`, pass bitmask, #pass, #fail).

Tests: SoC id, VDD, 32 MHz crystal (start-up time, HFINT-vs-HFXO sanity), SDA/SCL/INT shorts, I2C scan,
HDC2010 ID, measurement, INT line (data ready + wake, 4 thresholds), DC/DC under load, BLE controller + advertising.
The crystal's absolute accuracy needs the carrier build and a spectrum analyser / counter (tone at 2440.25 MHz).

## ble_sensor
Same behaviour as `firmware/C23/ble_sensor` in DRDY mode: the HDC2010 runs in auto mode at 0.2 Hz
(DRDY on INT, push-pull active high), each DRDY wakes the SoC (GPIO level interrupt, System ON sleep in between),
which reads T/RH, measures VDD and sends **one** non-connectable (ADV_NONCONN_IND, legacy) advertising event at 0 dBm.
Payload = flags `0x06`, BTHome v2 service data (UUID 0xFCD2, device info 0x40: packet id, battery %, temperature,
humidity, voltage; battery 3.0 V = 100 %, 2.2 V = 0 %), complete name `BSN-N52`. A failed sensor read sends
temperature -32768 / humidity 0, as the C23 firmware does. DC/DC enabled (`app.overlay`).
```
.\build.ps1 ble_sensor                      # product build, no console
.\build.ps1 ble_sensor -Conf debug.conf     # printk over RTT (build-ble_sensor-debug dir)
python hwtest\scripts\hwtest.py flash ble_sensor\build\zephyr\zephyr.hex
```

## ble_beacon_min (bare metal, lowest current)
Same advertisement as `ble_sensor` (`BSN-N52`, same address and BTHome payload), without Zephyr or a BLE stack. The
SoC sleeps in System OFF and the HDC2010's INT wakes it (a reset). It reads the sensor and VDD, sends one
ADV_NONCONN_IND on 37/38/39 by driving the RADIO registers directly, and goes back to System OFF. Measured 1.706 uA
average on A #3, against 12.8 uA for `ble_sensor` (details in [BRINGUP.md](BRINGUP.md)).
```
.\build.ps1 ble_beacon_min                  # -> ble_beacon_min\build\beacon.hex (own build.ps1, no west)
python hwtest\scripts\hwtest.py flash ble_beacon_min\build\beacon.hex
```
Power-cycle the board with the probe unplugged before measuring current (after SWD access System OFF is only emulated).

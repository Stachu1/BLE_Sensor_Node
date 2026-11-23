# BSN-N52 firmware

Firmware for `BSN-N52-A` (nRF52805), moved here from the separate AirTag project on 2026-11-23. The names were
changed to this repo's scheme: board `bsn_n52/nrf52805` (was `airtag/nrf52805`), advertised name `BSN-N52` (was
`BSN-52`), hwtest name `BSN-N52-HWTEST` (was `AirTag-HWTEST`). Boards flashed before the move still advertise the
old names until they are reflashed.

nRF Connect SDK v3.4.0 (Zephyr 4.4), custom board `bsn_n52/nrf52805` in `boards/oj/bsn_n52`.

Pins (from `hardware/N52/BSN-N52.kicad_sch`): P0.16 SCL, P0.18 SDA, P0.12 HDC2010 INT, P0.21 reset (J1). No external I2C
pull-ups (nRF internal ones are used), no LED, no UART, no 32 kHz crystal (LFCLK = RC).

Board status, MACs, tool usage and pitfalls: [BRINGUP.md](BRINGUP.md).

## Building and flashing

Same scheme as `firmware/N54` (and the `make` / `make jflash` targets of `firmware/C23`). From Git Bash, in the
app folder:

```sh
cd firmware/N52/hwtest     # or ble_sensor, ble_beacon_min
make                       # build (hwtest, ble_sensor: build/zephyr/zephyr.hex, ble_beacon_min: build/beacon.hex)
make jflash                # build, program, verify, reset and run with a SEGGER J-Link (tested path)
make stflash               # the same with an ST-Link through pyocd (python -m pip install pyocd), untested
make flash                 # the same through nrfutil (needs a J-Link)
make clean
```

Probe targets for every app ([`common/flash.mak`](common/flash.mak)):

| Target | What it does |
|---|---|
| `jflash` | J-Link Commander script: reset, halt, `loadfile` (erase touched pages, program, verify), reset, run |
| `stflash` | `hwtest.py flash <hex> --probe stlink` (pyocd, target `nrf52`) |
| `flash` | `west flash -r nrfutil` (Zephyr apps), `nrfutil device program` + reset (`ble_beacon_min`) |
| `soc` | does the SoC answer on SWD? DAP ID, FICR, UICR, expected BLE address. `PROBE=stlink` for an ST-Link |
| `jerase` | full chip erase with a J-Link |
| `jstatus` | J-Link: VTref, halt, registers, resume |
| `recover` | `nrfutil device recover` (full erase, lifts APPROTECT) |

`JLINK_SPEED` sets the J-Link SWD speed in kHz (default 2000). The Zephyr apps use
[`common/west.mak`](common/west.mak): if an option changes, the next build starts from a clean build directory.
[`tools/ncs-env.sh`](tools/ncs-env.sh) puts the NCS toolchain and J-Link on PATH (`. tools/ncs-env.sh` to run west
by hand).

Build options:

| App | Option | Meaning |
|---|---|---|
| `hwtest` | `CARRIER=1` | end in a continuous RF carrier (tone at 2440.25 MHz) instead of BLE advertising |
| `hwtest` | `SKIP_DCDC=1` | skip the DC/DC test if the board boot-loops in it |
| `ble_sensor` | `LOG=1` | printk over RTT (`debug.conf`). Default `LOG=0` (product build, no console) |
| `ble_sensor`, `ble_beacon_min` | `DRDY=n` | HDC2010 auto-mode code, as `DRDY` on the C23: 1 = 120 s, 2 = 60 s, 3 = 10 s, **4 = 5 s (default)**, 5 = 1 s, 6 = 0.5 s, 7 = 0.2 s. `DRDY=0`: one reading and one advert after boot, then no more wakes (floor) |

`build.ps1` (PowerShell) still works for the default builds (`.\build.ps1 hwtest`, `-Carrier`, `-SkipDcdc`,
`-Conf debug.conf`, `.\build.ps1 ble_beacon_min`) but has no `DRDY` option. Use `make`.

## hwtest
`make run` flashes the hwtest build, waits for the tests and prints the report, `make report` reads the report of
a running hwtest. Both take `PROBE=stlink`. The script can also be called directly (J-Link tested, ST-Link through
pyocd untested, see BRINGUP.md):
```
python hwtest/scripts/hwtest.py soc      # does the SoC answer on SWD (DAP, FICR, UICR)
python hwtest/scripts/hwtest.py run      # flash + run + print the report
python hwtest/scripts/hwtest.py report   # just read the report from RAM
```
Report channels: RAM struct `hwtest_report` (what the script reads), RTT console (`printk`, repeats every 5 s),
BLE advertisement `BSN-N52-HWTEST` (manufacturer data: `HW`, pass bitmask, #pass, #fail).

Tests: SoC id, VDD, 32 MHz crystal (start-up time, HFINT-vs-HFXO sanity), SDA/SCL/INT shorts, I2C scan,
HDC2010 ID, measurement, INT line (data ready + wake, 4 thresholds), DC/DC under load, BLE controller + advertising.
The crystal's absolute accuracy needs the carrier build (`make CARRIER=1 jflash`) and a spectrum analyser or an SDR
near the board (no RF connector, the carrier is picked up radiated). The tone sits at 2440.25 MHz (carrier + GFSK
deviation).

## ble_sensor
Same behaviour as `firmware/C23/ble_sensor` in DRDY mode: the HDC2010 runs in auto mode (0.2 Hz, `DRDY=4`)
(DRDY on INT, push-pull active high), each DRDY wakes the SoC (GPIO level interrupt, System ON sleep in between),
which reads T/RH, measures VDD and sends **one** non-connectable (ADV_NONCONN_IND, legacy) advertising event at 0 dBm.
Payload = flags `0x06`, BTHome v2 service data (UUID 0xFCD2, device info 0x40: packet id, battery %, temperature,
humidity, voltage; battery 3.0 V = 100 %, 2.2 V = 0 %), complete name `BSN-N52`. A failed sensor read sends
temperature -32768 / humidity 0, as the C23 firmware does. DC/DC enabled (`app.overlay`).
```sh
cd firmware/N52/ble_sensor
make jflash                 # product build, no console, 5 s
make LOG=1 jflash           # printk over RTT
```

## ble_beacon_min (bare metal, lowest current)
Same advertisement as `ble_sensor` (`BSN-N52`, same address and BTHome payload), without Zephyr or a BLE stack. The
SoC sleeps in System OFF and the HDC2010's INT wakes it (a reset). It reads the sensor and VDD, sends one
ADV_NONCONN_IND on 37/38/39 by driving the RADIO registers directly, and goes back to System OFF. Measured 1.706 uA
average on A #3, against 12.8 uA for `ble_sensor` (details in [BRINGUP.md](BRINGUP.md)).
```sh
cd firmware/N52/ble_beacon_min
make jflash                 # 5 s, as measured (1.706 uA)
make DRDY=7 jflash          # 0.2 s: the average current at this rate gives the charge per event
make DRDY=0 jflash          # one advert after power-up, then System OFF for good: the floor
```
Plain GCC from the NCS toolchain with Nordic's MDK headers, no west. `make` gives the same image as `build.ps1`
(checked byte for byte, 2400 B).
Power-cycle the board with the probe unplugged before measuring current (after SWD access System OFF is only emulated).

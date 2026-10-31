# BSN-C23 firmware (TI CC2340R5)

Firmware for `BSN-C23-A` boards. The bring-up and early test procedure is in
[BRINGUP.md](BRINGUP.md).

| Project | Output | Purpose |
|---|---|---|
| [`hwtest/`](hwtest) | `bsn_c23_hwtest.out` | Bring-up self-test with no BLE stack. It checks clocks, supply, I2C, the HDC2010 and its INT line, prints PASS/FAIL on the UART, then logs readings every 2 s. |
| [`ble_sensor/`](ble_sensor) | `bsn_c23_ble_sensor.out` | The sensor node. Reads the HDC2010 every 10 s and broadcasts temperature, humidity and battery as [BTHome v2](https://bthome.io/format/) advertisements (non-connectable, 1 s interval). |
| [`cwtest/`](cwtest) | `bsn_c23_cwtest.out` | RF test. Transmits an unmodulated carrier forever (default 2440 MHz, 0 dBm) for harmonic and spurious measurements. See [RF carrier test](#rf-carrier-test). |
| [`pwrtest/`](pwrtest) | `bsn_c23_pwrtest.out` | Current measurements. Holds the board in one power state per build (standby, shutdown, sensor polling, DRDY wake), with no BLE and no UART. See [Current test](#current-test). |
| [`common/`](common) | | Board pin map (`bsn_board.h`), UART logger, HDC2010 and SHTC3 drivers |
| [`test/`](test) | | Host unit tests for the drivers and the BTHome payload, run against a fake I2C bus |

## Toolchain

Installed on the dev PC on 2026-10-22. Everything lives under `C:\ti`:

| Tool | Version | Path | Used for |
|---|---|---|---|
| SimpleLink Low Power F3 SDK | 9.23.00.27 | `C:\ti\simplelink_lowpower_f3_sdk_9_23_00_27` | Drivers, BLE5-Stack, FreeRTOS |
| SysConfig | 1.26.4 (installed by the SDK) | `C:\ti\sysconfig_1.26.4` | Pin mux, CCFG and BLE config code generation |
| TI Arm Clang | 4.0.4.LTS | `C:\ti\ti-cgt-armllvm_4.0.4.LTS` | Compiler. This is the version the SDK was validated with. |
| Code Composer Studio | 21.0.1 (wireless MCU support only) | `C:\ti\ccs2101` | Debugging, XDS110 drivers, `DSLite` flasher, `gmake` |
| GNU make | any 4.x | `C:\ti\ccs2101\ccs\utils\bin\gmake.exe` or the STM32CubeIDE `make` already on PATH | Command-line builds |

CCS 21 also includes TI Arm Clang 5.1.1.LTS and SysConfig 1.28.1. The command-line build doesn't use
them. It uses the SDK-validated versions above.

To install from scratch on another PC:

1. **CCS**: download from https://www.ti.com/tool/download/CCSTUDIO and install with the
   "SimpleLink Wireless MCUs" (PF_WCONN) component. Admin rights are needed for the probe drivers.
2. **SDK**: download from https://www.ti.com/tool/download/SIMPLELINK-LOWPOWER-F3-SDK (version 9.23.00.27)
   and install to `C:\ti`. It installs SysConfig 1.26.4 alongside.
3. **Compiler**: download TI Arm Clang 4.0.4.LTS from https://www.ti.com/tool/download/ARM-CGT-CLANG and
   install so that `C:\ti\ti-cgt-armllvm_4.0.4.LTS\bin\tiarmclang.exe` exists.
4. If anything is installed elsewhere, override the paths in [`imports.mak`](imports.mak), e.g.
   `make TI_ROOT=D:/ti`.

## Building

From Git Bash:

```sh
cd firmware/C23/hwtest     # or ble_sensor
make                       # SysConfig + compile + link -> build/<name>.out and .hex
make clean
```

`ble_sensor` takes build options for power measurements. Changing them rebuilds automatically:

```sh
make LOG=0                              # no UART logging (always use for current measurements)
make LOG=0 ADV_MS=100 TX_DBM=0          # advertising interval (ms) and TX power (dBm, rounded down to the PA table)
make LOG=0 SENSOR_S=0                   # read the sensor once at boot, then never wake for it
make LOG=0 SENSOR_S=0 ADV=0             # start the BLE stack but never advertise (floor with the stack idle)
```

Defaults: `LOG=1`, `SENSOR_S=10`, `ADV_MS=0` (keep `ble_sensor.syscfg`, 1 s), `TX_DBM=0`, `ADV=1`.
Results: [`hardware/C23/testing/Power/POWER_MEASUREMENTS.md`](../../hardware/C23/testing/Power/POWER_MEASUREMENTS.md).

Host unit tests need any host C compiler (`gcc`, `clang`, or `zig cc` via `pip install ziglang`):

```sh
CC="python -m ziglang cc" sh test/run.sh
```

To edit pins, clocks or BLE parameters graphically, run `make syscfg-gui`, or edit the
`.syscfg` file directly. It is plain JavaScript.

## Hardware you need

- **An XDS110 debug probe.** Any of these works:
  - TI **LP-XDS110** or **LP-XDS110ET** standalone probe. The ET version also measures current
    (EnergyTrace), which is useful for the power work.
  - The XDS110 half of any SimpleLink LaunchPad (e.g. LP-EM-CC2340R5). Remove the jumpers between the
    XDS110 and the target MCU and run jumper wires from the XDS110 side to the board. The LaunchPad's
    back-channel UART can then also receive the log, so no separate USB-UART adapter is needed.
  - **SEGGER J-Link** (J-Link software V7.92 or later, V9.62 is installed). Use `make jflash`,
    `make jerase` and `make jstatus` instead of `flash`/`erase`/`probe`. Wiring is in BRINGUP.md, stage 2.
- **A 3.3 V USB-UART adapter**, unless you use the XDS110 back-channel UART.
- **Bench supply** set to 3.0 V with an adjustable current limit, for first power-on.
- Pogo pins or fine wire to reach the test points.

### Connections

| Signal | Board | XDS110 (10-pin Cortex debug / LaunchPad header) | USB-UART |
|---|---|---|---|
| SWDIO | TP3 (DIO16) | TMS/SWDIO | |
| SWCLK | TP5 (DIO17) | TCK/SWCLK | |
| nRESET | TP4 | nRESET (optional, enables hardware reset) | |
| VDD sense | TP9 | VTREF (pin 1), sense only, doesn't supply | |
| GND | TP10 | GND | GND |
| UART TX (board to PC) | TP2 (DIO13) | RXD (back-channel) | RX |
| UART RX (PC to board) | TP6 (DIO20) | not needed | **leave unconnected** |

Leave TP6 unconnected. The firmware never reads the UART, and an adapter's TX line would back-power
the board through the I/O protection diodes while the board is off.

**Power:** the target config [`targetConfigs/CC2340R5_XDS110.ccxml`](targetConfigs/CC2340R5_XDS110.ccxml)
selects *target-supplied power*, so the probe never drives VDD. Power the board from the bench supply or
its CR2032. **Never power the board from a probe or LaunchPad 3.3 V rail with a coin cell fitted**: the
CR2032 isn't rechargeable and would be back-charged.

## Flashing

```sh
cd firmware/C23/hwtest     # or ble_sensor
make probe                 # optional: the XDS110 should be listed
make flash                 # builds if needed, then chip erase + program + verify + run
```

`make flash` runs
`DSLite flash -c ../targetConfigs/CC2340R5_XDS110.ccxml -e -f -v -u build/<name>.out`.
`DSLite.exe` lives in `C:\ti\ccs2101\ccs\ccs_base\DebugServer\bin`.

If the probe connects but the target doesn't respond (e.g. firmware that sleeps forever or reconfigures the
SWD pins), run `make erase`. It runs TI's `cc23xx-unlock-debug-access` chip erase through the ROM, which
works even when the application has locked SWD out.

Alternatives:

- **UniFlash** (https://www.ti.com/tool/UNIFLASH) is a GUI that loads the same `.out` or `.hex` with the same probe.
- **ROM serial bootloader**: not usable on rev A. The UART pins don't match any of the ROM bootloader's
  pin sets (see BRINGUP.md, "Notes for rev B"), and the CCFG generated here disables it after the first flash.

### Without a UART adapter

`hwtest` can keep its log in RAM, to be read back over the J-Link:

```sh
cd firmware/C23/hwtest
make clean && make jflash EXTRA_CFLAGS=-DBSN_LOG_RAM=1    # then power-cycle the board
python ../tools/jlink_log.py build/bsn_c23_hwtest.map     # prints the log, the target keeps running
```

This build keeps the device out of standby, because the J-Link can't attach to a CC2340 in standby
("No CFG-AP detected", even with nRESET wired). The same applies to any image that sleeps: to reflash one,
retry `jflash` in a loop while power-cycling the board, so that a connect attempt lands in the boot window.

## RF carrier test

`cwtest` starts a continuous unmodulated carrier at boot and never stops it. It prints the frequency,
the actual PA setting, VDDS and the HFXT cap trim in use once on the UART, then leaves the UART idle.

```sh
cd firmware/C23/cwtest
make flash                                # 2440 MHz, 0 dBm (the power ble_sensor advertises at)
make flash FREQ_MHZ=2402 TX_DBM=8         # 2360..2500 MHz, -20..+8 dBm, rounded down to the PA table
```

Changing `FREQ_MHZ`, `TX_DBM` or `TX_HALF_DB` rebuilds automatically. To stop the carrier, flash another image.
With a J-Link instead of the XDS110, use `make jflash` and power-cycle the board afterwards.

Frequency offset and output power measured on rev A: [`hardware/C23/testing/RF/RF_CARRIER.md`](../../hardware/C23/testing/RF/RF_CARRIER.md).

- Run it from the bench supply. A continuous carrier draws several mA (more at +8 dBm), which a CR2032 can't
  supply for long, and the sagging voltage changes the output.
- Disconnect the probe and UART adapter during the measurement, or at least keep their cables away from the
  antenna. They can pick up and re-radiate harmonics.
- 2nd to 5th harmonics are at 4.88, 7.32, 9.76 and 12.2 GHz for a 2440 MHz carrier. Check 2402 and 2480 MHz
  as well (the BLE advertising channels 37 and 39).

## Current test

`pwrtest` puts the board into one fixed state, chosen at build time, for an ammeter in series with the supply.
Results and procedure: [`hardware/C23/testing/Power/POWER_MEASUREMENTS.md`](../../hardware/C23/testing/Power/POWER_MEASUREMENTS.md).

```sh
cd firmware/C23/pwrtest
make jflash MODE=standby                 # standby forever: the sleep floor
make jflash MODE=shutdown                # shutdown: the board baseline
make jflash MODE=idle                    # standby disallowed, CPU in WFI
make jflash MODE=active                  # CPU spinning
make jflash MODE=sensor PERIOD_MS=97     # HDC2010 polled by the MCU timer
make jflash MODE=sensor_irq HDC_AMM=7    # HDC2010 auto mode, DRDY wakes the MCU from standby
make jflash MODE=shutdown_wake HDC_AMM=7 # HDC2010 auto mode, DRDY wakes the MCU from shutdown
```

Every build puts the SHTC3 to sleep at boot (`SHTC3_SLEEP=0` leaves it idle) and waits 5 s before entering its state.
Changing a parameter rebuilds automatically.

- After `jflash`, unplug **all** J-Link wires and do a full power-on reset (TP9 at 0 V). Otherwise the CC2340 stays
  in the ROM at a few mA, or the probe keeps the debug logic powered.
- Bypass the ammeter while flashing. Its µA-range shunt starves the board when the debugger wakes it.
- For the event modes, run the events at 5–10 Hz so every meter reading averages several of them. Get the charge
  per event from `(I_avg − I_floor) × period`. The real period can be read from `sensorEvents` over SWD
  (address in `build/bsn_c23_pwrtest.map`).

## Debugging in CCS

1. Open CCS 21 and open any workspace folder.
2. *View > Target Configurations*. Import `firmware/C23/targetConfigs/CC2340R5_XDS110.ccxml`, right-click it, then
   *Start Project-less Debug*.
3. When connected: *Run > Load > Load Program...* and pick `build/bsn_c23_hwtest.out` (or the BLE one).
   The ELF contains absolute source paths, so breakpoints in the `.c` files work.
4. Useful views: *Registers* (CKMD, PMCTL), *Memory Browser* at `0x4E000000` (FCFG: factory BLE
   address, part ID), and the *Runtime Object View* for FreeRTOS tasks and stack high-water marks.

## Configuration decisions

These come from the rev A schematic (`hardware/C23/BSN-C23.kicad_sch`). If the hardware changes, update
`common/bsn_board.h` and both `.syscfg` files together.

| Decision | Why |
|---|---|
| `CCFG.srcClkLF = "LF RCOSC"` | X2 (32.768 kHz) is DNP. With the default "LF XOSC" the device would wait for a crystal that isn't there. The BLE module then adds 1500 ppm of sleep-clock margin, which costs a little extra RX-window time in connections but nothing for a pure broadcaster. |
| ROM bootloader pin trigger off | The CC23xx default trigger pin is DIO21, which is the HDC2010 INT line on this board. |
| Pull-down on DIO21 | The HDC2010 INT output is high-Z until configured. A floating input wastes current. |
| HFXT cap-array trim overridden to Q1 = Q2 = 44 | With the factory trim (35) the carrier was +30 ppm high. 44 brings it to +2 ppm (BRINGUP.md stage 6, `hardware/C23/testing/RF/RF_CARRIER.md`). Set in `ble_sensor.syscfg` and `cwtest.syscfg`. |
| Public BLE address | Uses the factory address from FCFG, so the address printed by hwtest is the one you'll see in a scanner. |
| BTHome v2 payload | Open format that Home Assistant, Theengs and BTHome-aware scanner apps decode with no custom code. Layout is in `ble_sensor/bthome.c`. |
| Broadcaster only, no GATT | Lowest power and smallest stack. A connectable variant with the Device Information Service (hardware revision) can be added later. |
| SHTC3 (U2) still probed | U2 is DNP on rev A, but the self-test reports it if fitted, for sensor comparison. |

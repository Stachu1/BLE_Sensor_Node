# BSN-N54 firmware (Nordic nRF54L05)

> **Concluded at rev A.** The N54 was compared with the C23 on rev A and rev B uses the CC2340R5; see
> [`MCU_DECISION.md`](../../hardware/MCU_DECISION.md). This folder is kept as the record of that comparison.

Firmware for `BSN-N54-A` boards. It mirrors [`firmware/C23`](../C23) app for app and option for option, so the
two variants can be measured the same way. The bring-up and test procedure is in [BRINGUP.md](BRINGUP.md).

| Project | Purpose |
|---|---|
| [`hwtest/`](hwtest) | Bring-up self-test with no BLE stack. Checks the HFXO and the LF clock (RC, or X2 with `LFCLK=xtal`), VDD, I2C, the HDC2010 and its INT line, and the SHTC3 (reported as not present if U2 isn't fitted). Prints PASS/FAIL on the UART (or RTT), then logs readings every 2 s. |
| [`ble_sensor/`](ble_sensor) | The sensor node. Reads the HDC2010 every 10 s and broadcasts [BTHome v2](https://bthome.io/format/) advertisements (legacy non-connectable, 3 channels, 1 s interval). Same payload layout as C23, name `BSN-N54`. |
| [`cwtest/`](cwtest) | RF test. Transmits an unmodulated carrier forever (default 2440 MHz, 0 dBm), or single FSK tones (`PATTERN=1/2`) for checking the carrier offset. |
| [`pwrtest/`](pwrtest) | Current measurements. Holds the board in one power state per build, with no BLE and no UART. |
| [`common/`](common) | Board devicetree overlay (`bsn_n54.overlay`), board header, HDC2010/SHTC3 drivers (ported from C23), VDD reading, shared build rules |
| [`tools/`](tools) | `ncs-env.sh`: puts the NCS toolchain and J-Link on PATH. `rtt_log.sh`: prints the RTT log of an `RTT=1` image |

## Toolchain

| Tool | Version | Path |
|---|---|---|
| nRF Connect SDK | v3.4.0 | `C:\ncs\v3.4.0` |
| NCS toolchain bundle (west, CMake, Ninja, Zephyr SDK, nrfutil) | `dcbdc366a1` | `C:\ncs\toolchains\dcbdc366a1` |
| nrfutil device | 2.19.0 | in the toolchain bundle |
| SEGGER J-Link | V9.82 | `C:\Program Files\SEGGER\JLink_V982` |
| GNU make | any 4.x | the STM32CubeIDE `make` already on PATH |

There is no custom board definition. The apps build for the DK target `nrf54l15dk/nrf54l05/cpuapp`, and
[`common/bsn_n54.overlay`](common/bsn_n54.overlay) changes it to this board:

- UART20 on P1.06 (TX, TP9) and P1.07 (RX, TP10), no flow control.
- I2C on **i2c30**, SDA P0.00 and SCL P0.03, 400 kHz. P0 pins can only use serial instance 30, so the DK's
  VCOM1 (uart30, which sits on P0.00–P0.03) is disabled.
- HDC2010 INT on P0.01 with a pull-down (`zephyr,user` `hdc-int-gpios`).
- VDD on SAADC channel 0 (internal VDD input).
- X1 32 MHz: internal load caps, 7 pF. X2 32.768 kHz (if fitted): internal load caps, 12.5 pF. DC/DC on (L1 fitted).
- Removed: the DK LEDs, buttons, PWM LED, external flash (spi00), spi22 and NFC.

## Building

From Git Bash:

```sh
cd firmware/N54/hwtest     # or ble_sensor, cwtest, pwrtest
make                       # west build -> build/zephyr/zephyr.hex
make clean
```

Each makefile turns its options into `west build ... -- -D...` (rules in [`common/west.mak`](common/west.mak)).
If an option changes, the next build starts from a clean build directory, so a full build takes about 2 minutes.
To run west by hand, first `. ../tools/ncs-env.sh`.

`ble_sensor` takes the same build options as C23:

```sh
make LOG=0                              # no UART logging (always use for current measurements)
make LOG=0 ADV_MS=100 TX_DBM=0          # advertising interval (ms) and TX power (dBm)
make LOG=0 SENSOR_S=0                   # read the sensor once at boot, then never wake for it
make LOG=0 SENSOR_S=0 ADV=0             # start the BLE stack but never advertise (floor with the stack idle)
```

Options for every app:

```sh
make flash RTT=1             # console over SEGGER RTT through the J-Link, no USB-UART needed; read with: sh ../tools/rtt_log.sh
make flash LFCLK=xtal        # LF clock from X2; default LFCLK=rc (internal RC, X2 not fitted, same as C23's LFOSC)
make flash HFXO_CL_FF=12000  # X1 load capacitance in fF (4000..17000, 250 fF steps), overrides bsn_n54.overlay
make flash DCDC=0            # main regulator as LDO instead of DC/DC (for checking L1)
```

Switching apps or options rebuilds from scratch (about 2 minutes). If CMake has to re-run configure in an
existing build directory, NCS aborts with "malformed string literal ... MBEDTLS_CONFIG_FILE"; `west.mak` then
retries with a clean build automatically, so a `FATAL ERROR` line followed by a successful build is expected.

**HFXO trim:** `bsn_n54.overlay` sets X1 to **11.75 pF**, measured on board #2 with `cwtest`. The datasheet value
(7 pF) put the carrier +127 ppm high. See [`hardware/N54/testing/RF/RF_CARRIER.md`](../../hardware/N54/testing/RF/RF_CARRIER.md).

**LF clock calibration:** with `LFCLK=rc` the RC is calibrated as rarely as the BLE stack allows
(`common/lfrc.conf`): die temperature every 8 s, recalibration only after a 0.5 °C change or every ~4.4 min.
The NCS default (every 4 s) cost about 0.7 µA of floor current. MPSL refuses an uncalibrated RC at build time, and
a period above 8 s makes `bt_enable()` fail at run time.

Defaults: `LOG=1`, `SENSOR_S=10`, `ADV_MS=1000`, `TX_DBM=0`, `ADV=1`. `TX_DBM` selects
`CONFIG_BT_CTLR_TX_PWR_PLUS_<n>` or `_MINUS_<n>`, so it has to be a step the nRF54L supports (for example −8,
−4, 0, +4, +8). An unsupported value only gives a Kconfig warning and falls back to 0 dBm, so check
`CONFIG_BT_CTLR_TX_PWR_DBM` in `build/zephyr/.config`.

Differences from C23 that matter for the comparison:

- The controller picks the TX power at build time (`CONFIG_BT_CTLR_TX_PWR_*`) rather than from a PA table at run time.
- The payload is reloaded synchronously (`bt_le_adv_update_data`), so the C23 build's extra 1 s wake-ups don't
  exist here. Measure `Q_adv` with `SENSOR_S=0` on both boards, as in the C23 power notes.
- The address is the FICR static random address (C23 uses its factory public address). `hwtest` prints it.
- Both boards use their internal RC as the LF clock by default (X2 not fitted on board #1). `LFCLK=xtal` measures the N54 with the crystal.

## Flashing

Wire the J-Link as in [BRINGUP.md](BRINGUP.md#stage-2--swd-connection). Then:

```sh
make flash                 # builds if needed, programs with nrfutil (through the J-Link), then resets and runs
make jflash                # the same with the SEGGER J-Link runner
make recover               # nrfutil device recover: full erase and lifts the access-port protection
```

A brand new or locked nRF54L refuses to program until it has been recovered once. If `make flash` reports
an access-protection or `ERASEPROTECT` error, run `make recover` and flash again.

The `jlink` runner uses the DK's J-Link device name `nRF54L15_M33`. This works for the smaller L05 as long as
the image fits. Prefer `make flash`.

## RF carrier test

```sh
cd firmware/N54/cwtest
make flash                                # 2440 MHz, 0 dBm
make flash FREQ_MHZ=2402 TX_DBM=8         # 2360..2500 MHz, TXPOWER -40..+8 dBm (rounded down to the table)
make flash PATTERN=1                      # all-1 packets: one tone at carrier + deviation
make flash PATTERN=2                      # all-0 packets: one tone at carrier - deviation
```

The firmware starts the HFXO, sets `RADIO.MODE` (BLE 1M), `TXPOWER` and `FREQUENCY`, triggers `TXEN` and
leaves the radio in TXIDLE, where it transmits the unmodulated carrier. This is the register sequence of
the NCS `radio_test` sample, without its `START`. The settings are printed once on TP9 (or over RTT with `RTT=1`).

`PATTERN=1/2` send back-to-back packets with whitening and CRC off. The midpoint of the two tones is the true
carrier and their spacing the FSK deviation (about 500 kHz), whatever the radio does while idle. On rev A this
confirmed that the TXIDLE carrier is centred.

Power-cycle after flashing: the carrier only starts after a power-on reset. Run it from the bench supply with the
current limit at 40 mA or more (at 20 mA, +8 dBm browns the board out), and disconnect the probe and UART during
the measurement, as for C23.

## Current test

```sh
cd firmware/N54/pwrtest
make flash MODE=standby                 # System ON idle forever: the sleep floor
make flash MODE=shutdown                # System OFF
make flash MODE=bareoff                 # System OFF with every GPIO reset to its default first
make flash MODE=active                  # CPU spinning
make flash MODE=sensor PERIOD_MS=97     # HDC2010 polled by the MCU timer
make flash MODE=sensor_irq HDC_AMM=7    # HDC2010 auto mode, DRDY wakes the MCU
```

Every build sends the SHTC3 its sleep command (`SHTC3_SLEEP=0` leaves it idle) and waits 5 s before entering
its state. `pwrtest` is always built without the UART. `sensorEvents` and `sensorErrors` are global variables
that can be read over SWD, as on C23.

Pin settings survive System OFF, so the difference between `MODE=shutdown` and `MODE=bareoff` is what the
firmware's pin configuration costs in System OFF.

Use the procedure in [`hardware/C23/testing/Power/POWER_MEASUREMENTS.md`](../../hardware/C23/testing/Power/POWER_MEASUREMENTS.md):
unplug all J-Link wires after flashing, then short VDD (TP1) to GND (TP4) for about 1 s before measuring. After a
debug session the nRF54L stays in debug-powered mode (and only emulates System OFF) until a power-on reset.

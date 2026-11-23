# BSN-N52-A bring-up

Status of the first three boards, how the firmware tools work and what we learned. Written 2026-11-23.
Build and layout details: [README.md](README.md).

## Boards

All three: nRF52805-CAAA (variant `AAA2`, package 0x2004, 24 kB RAM, 192 kB flash), flashed and tested with a
SEGGER J-Link (S/N 853003024).

| Board | nRF device ID | BLE address | hwtest | App flashed | Notes |
|---|---|---|---|---|---|
| A #1 | `82bf85646c20248b` | `DF:55:EE:37:04:CD` | 11/11 pass | not recorded | The first board, used to develop the tests. Last hwtest run was before the bus-recovery change. |
| A #2 | `6023d594055cb484` | `C2:D7:6D:9C:B3:20` | 11/11 pass (after sensor rework) | yes | First attempt failed: SDA and INT held low by U1 (bad solder / short at the HDC2010). Fixed by reworking the sensor. |
| A #3 | `47a70671fbe71ff6` | `DB:1C:AA:DB:F2:9D` | 11/11 pass | yes | Transmits correct BTHome data (confirmed on the scanner). First flash attempt gave "Failed to power up DAP", the retry worked. |

**BLE addresses:** `ble_sensor` advertises with the *identity* address, a fixed static random address derived from the
chip's factory address registers (FICR `DEVICEADDR`, top two bits set). It does not rotate. The address is not the
same as the device ID above. The values in the table were taken from the scanner. With a board connected,
`python firmware\N52\hwtest\scripts\hwtest.py soc` prints the address the script expects ("BLE address"); that
derivation has not been compared with these three yet.

### Hwtest results (last run per board)

| Test | A #2 | A #3 | Pass criterion |
|---|---|---|---|
| SoC identity | nRF52805, 24k/192k | same | part `0x52805`, RAM 24, flash 192 |
| VDD | 2995 mV | 2998 mV | 1.8 to 3.6 V |
| 32 MHz crystal | start 364 us | start 367 us | starts in under 2 ms, internal RC agrees within 3 % |
| SDA/SCL/INT pins | clean | clean | no stuck pins, no bridges |
| I2C scan | only 0x40 | only 0x40 | exactly one device, 0x40 |
| HDC2010 ID | 0x5449 / 0x07D0 | same | TI manufacturer + device ID |
| HDC2010 measurement | 32.9 C, 22.2 %RH | 32.9 C, 15.8 %RH | plausible values, no all-0 / all-1 |
| INT line | data ready + 4 thresholds | same | INT asserts, wakes the CPU, releases |
| DC/DC | 2993 to 2996 mV | 2998 to 3006 mV | VDD holds (+-150 mV) with the DC/DC on under load |
| Radio / BLE | pass | pass | BLE controller starts and advertises |

The crystal check is a sanity check only: it compares the crystal with the internal RC (HFINT, spec +-1.5 %). The
three boards showed +0.7 % to +2.5 %. A #3 was nearest the 3 % limit. The absolute frequency (ppm) still needs the
carrier build and a counter or spectrum analyser.

## The ble_sensor app

- HDC2010 in auto mode at 0.2 Hz, DRDY on INT (push-pull, active high). Each DRDY wakes the SoC, which reads T/RH,
  measures VDD, sends **one** ADV_NONCONN_IND event at 0 dBm and sleeps.
- Same BTHome v2 payload as `firmware/C23/ble_sensor`: flags 0x06, service data UUID 0xFCD2, device
  info 0x40, objects packet id (0x00), battery % (0x01), temperature (0x02), humidity (0x03), voltage (0x0C), then the
  complete name `BSN-N52`. Failed sensor read: temperature -32768, humidity 0.
- Fixed MAC (`BT_LE_ADV_OPT_USE_IDENTITY`).
- Temperature uses T = 165 * raw / 2^16 - 40 C (datasheet Equation 1, same as the C23 driver). The -40.5 C offset
  in the datasheet applies only to the 8-bit TEMP_THR_L/H registers (Equations 5 and 6), not to the result registers.
  Earlier builds wrongly used -40.5 and read 0.5 C low.

## The ble_beacon_min app (bare metal, System OFF)

Written 2026-11-23 because `ble_sensor` drew far more than the datasheet suggests. Same advertisement as `ble_sensor`
(name `BSN-N52`, same identity address, same BTHome v2 payload), but no Zephyr and no BLE stack:

- The SoC sleeps in **System OFF** (no LFCLK, no RTC, no RAM retention). The HDC2010's INT (P0.12, GPIO SENSE high)
  wakes it, and the wake is a reset.
- Per wake: start HFXO, read status + data over TWIM at 250 kHz, read VDD (SAADC), send one ADV_NONCONN_IND on
  channels 37/38/39 by driving the RADIO registers directly (CPU in WFE while the radio works), System OFF again.
- The BTHome packet id is kept in `POWER->GPREGRET`, which is retained in System OFF.
- Cold boot (power-on, pin reset, debugger): I2C bus recovery, HDC2010 soft reset and auto mode at 0.2 Hz, then
  System OFF until the first DRDY.
- Fault path: if the sensor does not answer or INT stays high, it sends the invalid-sensor packet, sleeps 5 s on the
  RTC (LFRC) and resets into the cold path.
- 2.4 kB of code. Built with `.\build.ps1 ble_beacon_min` (own `build.ps1`: NCS GCC + Nordic MDK headers).

Checked on A #3: the scanner receives it, and over SWD the packet counter rose 2 -> 5 in 11 s (one wake per ~5 s).

### Current measurement (A #3, 2026-11-23)

Also in [`hardware/N52/testing/Power/POWER_MEASUREMENTS.md`](../../hardware/N52/testing/Power/POWER_MEASUREMENTS.md), with the
comparison to `BSN-C23-B`.

Bench DMM, 100 PLC, autozero on, 10 mA range, board powered from the supply with the J-Link unplugged and the board
power-cycled after flashing.

| Firmware | Mean | Std dev | Samples |
|---|---|---|---|
| `ble_sensor` (Zephyr + BLE controller, System ON idle) | 12.765 uA | 3.3 uA | 150 |
| `ble_beacon_min` (bare metal, System OFF) | **1.706 uA** | 1.985 uA | 685 |

7.5x lower. With Zephyr, the SoC stays in System ON idle: the BLE controller keeps the LFRC and RTC running and wakes
the HFXO every 4 s for the RC calibration. The bare-metal version has no timebase at all and only wakes on the
HDC2010's DRDY. The large std dev is the 5 s burst pattern seen through 100-PLC windows (a window either contains an
advertising event or not), not noise. On the 10 mA range the DMM offset error is of the order of the result, so the
absolute value should be confirmed on a lower range or with a PPK2.

Trade-offs: no connections, GATT or BLE OTA, and no advertising delay (fixed 5 s timing set by the HDC2010's own
oscillator). If the HDC2010 ever loses its configuration without driving INT, the beacon goes silent until it is
power-cycled (nothing else wakes it).

After flashing or any SWD access the debug interface stays powered and System OFF is only emulated (higher current;
the firmware handles the wake by hand there). **Always power-cycle with the probe unplugged before measuring.**

## Tools

### Build
```
cd firmware\N52
.\build.ps1 hwtest                       # firmware\N52\hwtest\build\zephyr\zephyr.hex
.\build.ps1 hwtest -Carrier              # ends in a continuous RF carrier at 2440.25 MHz, no BLE
.\build.ps1 hwtest -SkipDcdc             # skips the DC/DC test (use if a board boot-loops in it)
.\build.ps1 ble_sensor                   # product build, no console
.\build.ps1 ble_sensor -Conf debug.conf  # printk over RTT
.\build.ps1 <app> -Pristine              # clean build
```
Uses the installed nRF Connect SDK v3.4.0 (`C:\ncs`, toolchain `dcbdc366a1`). Output is in `<app>\build\zephyr\`.

### hwtest.py (`firmware\N52\hwtest\scripts\hwtest.py`)
```
python hwtest.py soc                    # does the SoC answer? DAP ID, FICR, UICR, BLE address
python hwtest.py run                    # flash the hwtest build, wait 9 s, print the report
python hwtest.py report                 # read the report from RAM (hwtest must be running)
python hwtest.py flash <hex>            # flash any hex, e.g. ..\..\ble_sensor\build\zephyr\zephyr.hex
```
The tests are 11 numbered checks. The report is also in RAM (symbol `hwtest_report`, found through
`zephyr.elf`), on RTT (printk, repeats every 5 s) and in the BLE advertisement `BSN-N52-HWTEST` (manufacturer data
`HW`, pass bitmask, number passed, number failed). The numbers after each result are test-specific values, explained
in `detail()` in `hwtest\src\tests.c`.

Typical new-board flow:
```
python hwtest.py soc                                                      # chip alive, note the BLE address
python hwtest.py run                                                      # all 11 must pass
python hwtest.py flash ..\..\ble_sensor\build\zephyr\zephyr.hex           # then check the scanner
```
Run these from `firmware\N52\hwtest\scripts`. `report` needs the hwtest build in `hwtest\build\zephyr` (it reads the
symbol address from there).

### Probes

| Probe | Status | How |
|---|---|---|
| SEGGER J-Link | **tested** | default. Uses `JLink.exe` from `C:\Program Files\SEGGER\JLink*`, nothing to install. `JLINK_EXE` sets another path, `JLINK_SPEED` the SWD speed in kHz (default 2000). |
| ST-Link | **not tested** | `--probe stlink` (or env `HWTEST_PROBE=stlink`). Uses pyocd: `python -m pip install pyocd`. Target is pyocd's built-in `nrf52` (nRF52832 memory map), which covers the nRF52805 flash range. Not run on this board: if programming the UICR (reset pin setting) fails, flash again or set it with a J-Link once. `--uid <serial>` picks one probe when several are connected; `python -m pyocd list` lists them. |

Wiring: the board has a TagConnect TC2030-NL (J1): VCC, SWDIO, RESET, SWCLK, GND (SWO not routed). The probe only
senses VCC, it does not power the board: **power the board from the battery or a supply**, otherwise the J-Link
reports `VTref=0.000V` / "Target voltage too low".

## Pitfalls found on rev A

- **No external I2C pull-ups.** The nRF internal pull-ups (about 13 kOhm) are used. Fine at 100 kHz, marginal faster.
- **No LED, UART or 32 kHz crystal**; only SWD, SDA, SCL and INT are wired. LFCLK is the internal RC.
- **The HDC2010 survives MCU resets.** It keeps its mode, and if the MCU resets in the middle of an I2C transfer it
  holds SDA low. Symptom: I2C hangs after a reset. The hwtest clocks the bus free (9 SCL pulses + STOP) and soft
  resets the sensor first. `ble_beacon_min` does the same on every cold boot; `ble_sensor` does not.
- **Zephyr's `gpio_pin_get_raw()` reports the output latch for driven pins**, and the enabled TWIM peripheral overrides
  SDA/SCL. For pin tests disable `NRF_TWIM0` and use the `NRF_P0` registers directly.
- **The Bluetooth controller (MPSL) requires the RC calibration** when the RC is the low-frequency clock, so the crystal
  check cannot assume the HFXO is off. It may start briefly for calibration.
- **Non-connectable advertising rotates the address by default** in Zephyr (a new non-resolvable address per start)
  unless `BT_LE_ADV_OPT_USE_IDENTITY` is set.
- **Read the HDC2010 status register before the data registers.** Reading the data clears DRDY, so a status read after
  it shows not-ready and the packet goes out with the invalid-sensor values (-327.68 C, 0 %RH).
- If the debugger fails with "Failed to power up DAP" right after flashing, just retry (seen once, A #3).

## Not tested yet

- Absolute crystal frequency (build with `-Carrier`, measure 2440.25 MHz).
- BLE range and antenna performance of the MIFA on the real boards.
- Average current on a lower meter range or with a PPK2 (the 10 mA range result is 1.706 uA, see above).
  For comparison, the C23 board measured about 4.8 uA at a 5 s DRDY interval.
- `ble_beacon_min` on A #1 and A #2.
- The ST-Link path of `hwtest.py`.
- The `soc` command's expected BLE address against the scanner values of A #1 and A #2 (A #3 matches:
  `DB:1C:AA:DB:F2:9D`).

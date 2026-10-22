# BSN-C23-A bring-up and early test plan

Work through the stages in order. Each stage checks only what the previous one already proved, so the
first failure points at a small area of the board. Number the boards (#1, #2, ...) with a marker as you
assemble them, and fill in the [results table](#results-log) per board.

Tools, wiring and the `make` commands are described in [README.md](README.md).

| Stage | What it proves | Needs |
|---|---|---|
| 0. Visual and ohmmeter | Assembly: no shorts, orientation | Microscope, DMM |
| 1. First power, blank chip | Power tree, regulators | Bench supply, DMM |
| 2. SWD connect | MCU alive, debug path | XDS110 |
| 3. `hwtest` firmware | Clocks, I2C, sensor, INT line, UART | XDS110, USB-UART |
| 4. `ble_sensor` firmware | Radio, antenna path, BLE stack | Phone with a BLE scanner |
| 5. Current baseline | Low-power behaviour | Ammeter or PPK2 / EnergyTrace |
| 6. RF checks | Crystal offset, range | Spectrum analyser or SDR, second person |

---

## Stage 0 — Visual and ohmmeter checks (unpowered)

Rev A population reminder: **DNP** = U2 (SHTC3), X2 (32 kHz), C9, C14, C15, C16, C19, C20, J1, L4.
Everything else is fitted.

- [ ] U1 (CC2340R5, QFN-24): pin-1 dot, no bridges on the 0.5 mm pitch, exposed pad soldered (check the side profile).
- [ ] U3 (HDC2010, 1.5 mm DSBGA): orientation (ball A1), sitting flat, and the sensor opening not
      covered in flux. **Don't wash the humidity sensor with IPA, and don't put flux on it**
      (see TI SNIA025). Reflow shifts RH by a few %RH; it recovers after rehydration (roughly 24 h at room
      conditions, or longer at high RH).
- [ ] X1 (48 MHz, 4-pad): orientation per footprint.
- [ ] L5 (10 µH DC/DC inductor), C10–C13 near U1.
- [ ] RF path: C7, L1, C8, C6, L2, L3, AE1 present and not tombstoned.
- [ ] BT1 holder polarity.

With a DMM (no battery, no supply):

| Measurement | Expected | Typical fault if wrong |
|---|---|---|
| TP9 (VDD) to TP10 (GND) | Climbs slowly into the kΩ to MΩ range while C5 (100 µF) charges; **not** < 100 Ω | Solder bridge, reversed cap, damaged U1 |
| C10 / C11 (VDDR) to GND | No short | Bridge at U1 pins 2/20, L5 |
| C13 (VDDD) to GND | No short | Bridge at U1 pin 16 |
| TP1 (SDA) to TP9, TP8 (SCL) to TP9 | about 4.7 kΩ | R1/R2 missing or wrong value |
| TP4 (nRESET) to TP9 | about 100 kΩ | R3 |

## Stage 1 — First power with a blank chip

Use the bench supply on TP9/TP10 (or the battery-holder contacts), **with no coin cell fitted**.
Set it to **3.0 V and limit the current to 20 mA**.

- [ ] Supply current is steady and in the low single-digit mA range. The blank device sits in the ROM
      waiting for a valid image or bootloader command. If it hits the 20 mA limit, switch off and go back to stage 0.
- [ ] Nothing gets warm (fingertip on U1 and L5).
- [ ] VDD (TP9) = 3.0 V.
- [ ] VDDR (C10/C11 pad) is about 1.5 V.
- [ ] VDDD (C13 pad) is about 1.28 V.
- [ ] nRESET (TP4) is at VDD.

Record the currents. The same numbers on every board means good consistency. An outlier with
otherwise normal behaviour usually means leakage (flux residue, a part fitted that should be DNP).

## Stage 2 — SWD connection

Wire the XDS110 as in README.md (SWDIO→TP3, SWCLK→TP5, GND→TP10, VTREF→TP9, nRESET→TP4). Keep powering
from the bench supply.

```sh
cd firmware/C23/hwtest
make probe      # the XDS110 must be listed
make erase      # first real conversation with the chip
```

**With a SEGGER J-Link** (e.g. J-Link PLUS Compact, 0.05" 9-pin Cortex-M connector):

| J-Link pin | Signal | Board |
|---|---|---|
| 1 | VTref (sense only, doesn't power the board) | TP9 |
| 2 | SWDIO | TP3 |
| 3 or 5 | GND | TP10 |
| 4 | SWCLK | TP5 |
| 10 | nRESET (optional) | TP4 |

Leave pins 6, 8 and 9 unconnected. Then run `make jstatus`: it must report VTref of about 3.0 V and
connect to `CC2340R5`. On a blank chip, SEGGER's connect sequence writes a default CCFG first, which is expected.
After that, use `make jflash` in place of `make flash`. `make jerase` is the chip erase.

- [ ] `make erase` (or `make jstatus` with a J-Link) completes without errors. This proves SWD, the debug access port and the flash
      controller work, all without needing the HFXT crystal (the ROM runs on the internal oscillator).

If it fails:

| Symptom | Check |
|---|---|
| `Error -260 ... connect to the XDS110 failed` | USB cable, or the probe isn't detected by `make probe` |
| Probe found, target doesn't respond | SWDIO/SWCLK swapped, VTREF not connected, no supply, nRESET held low, U1 soldering (pins 7, 8, 13) |
| Intermittent errors | Wires too long: keep SWD leads under about 15 cm and run GND next to them |

## Stage 3 — Hardware self-test (`hwtest`)

Connect the USB-UART adapter: **adapter RX → TP2**, GND → TP10. Leave TP6 unconnected. Open a terminal
(PuTTY is installed) on the adapter's COM port at **115200 8N1**, then:

```sh
cd firmware/C23/hwtest
make flash
```

The board starts after programming. Expected output (your address, part ID and readings will differ):

```
==== BSN-C23-A hwtest 0.1.0 (built Oct 22 2026 14:00:00) ====
Reset reason : SWD (debugger)
BLE address  : XX:XX:XX:XX:XX:XX
Part ID      : 0x.......
[PASS] HFXT 48 MHz (X1)
[PASS] LF clock (LFOSC)
[PASS] VDDS                   3004 mV
Die temp     : 24 C
[PASS] I2C open
I2C scan     : 0x40
[PASS] HDC2010 ID (U3 @0x40) manuf 0x5449 dev 0x07D0
[PASS] HDC2010 config
[PASS] HDC INT idle low
[PASS] HDC2010 trigger
[PASS] HDC INT level (DIO21)
[PASS] HDC INT edge IRQ
[PASS] HDC2010 DRDY status
[PASS] HDC INT cleared
[PASS] HDC2010 plausible      23.84 C  41.27 %RH
[INFO] SHTC3 (U2 @0x70)       not present (DNP on rev A)
==== Self-test: 13 passed, 0 failed -> PASS ====

#0 VDDS=3004 mV die=24 C | HDC2010 23.86 C 41.20 %RH | INT edges=2
#1 VDDS=3004 mV die=24 C | HDC2010 23.85 C 41.22 %RH | INT edges=3
```

Record the **BLE address** for each board; stage 4 uses it.

Then check that the readings respond to the environment:

- [ ] Breathe on U3: RH jumps by 10–30 %RH and temperature rises within a few seconds, then both recover.
- [ ] HDC2010 temperature is within about 1 °C of a reference thermometer. It may read a little high
      from board self-heating while the UART is printing.
- [ ] Die temperature (±few °C resolution) roughly agrees with the HDC2010.
- [ ] Short TP4 to GND briefly: the board restarts and prints `Reset reason : reset pin`.
- [ ] Power-cycle from the supply: `Reset reason : power-on`.

If any check FAILs:

| FAIL | Likely cause |
|---|---|
| No output at all | Adapter RX on the wrong test point, wrong COM port or baud rate, TX/RX swapped at the adapter. Use the CCS debugger to see if `main` runs. |
| `HFXT 48 MHz` | X1 orientation or soldering, X1 is the wrong part, a broken trace to U1 pins 21/22 |
| `LF clock` | Shouldn't happen with LFOSC. Check that the image was built from this repo (CCFG `srcClkLF`). |
| `VDDS` out of range | Supply setting; batteries below 1.8 V |
| `I2C scan: none` | R1/R2, SDA/SCL bridged, U3 not soldered or rotated, U3 without VDD (ball A1) |
| `HDC2010 ID` with other addresses found | Wrong part fitted, or ADDR (ball B1) not at GND, which moves the device to 0x41 |
| `HDC INT level` FAIL but ID PASS | Open trace between U3 ball C2 and U1 pin 10 (DIO21); probe TP7 with a scope while it runs |
| `HDC2010 plausible` | Sensor damaged or contaminated, or the formula is off; compare with SHTC3 if fitted |

## Stage 4 — BLE firmware (`ble_sensor`)

```sh
cd firmware/C23/ble_sensor
make flash
```

UART output:

```
==== BSN-C23-A ble_sensor 0.1.0 (built ...) ====
[SNS] HDC2010 ok
[BLE] stack ready, address 0xXXXXXXXXXXXX (same as in hwtest)
[BLE] advertising started (interval 1000 ms)
[SNS] #1 23.91 C 41.30 %RH VDDS 3004 mV
[SNS] #2 ...
```

With a J-Link, `make jflash` stops after programming. Unplug the J-Link USB, power the board off for
at least 30 s, then power it on. SEGGER's post-flash reset left the core halted in the ROM on board #1.

From the PC (any Bluetooth adapter, `pip install bleak`):

```sh
python ../tools/bsn_scan.py --mac FC:DE:C5:73:2F:4E          # one line per new reading
python ../tools/bsn_scan.py --mac FC:DE:C5:73:2F:4E --csv b1.csv
```

Windows scans at a low duty cycle and reports only a fraction of the 1 s adverts, so new readings
may appear several seconds late. Use the packet counter, not arrival times, to check the 10 s period.

Or on a phone, install **nRF Connect for Mobile** (Nordic) or **TI SimpleLink Connect** and scan:

- [ ] A device named **BSN-C23** appears with the address from stage 3.
- [ ] Its advertising data contains service data for UUID **0xFCD2**, e.g.
      `40 00 07 01 64 02 4F 09 03 22 10 0C BC 0B`, which decodes as:
      `40` BTHome v2 unencrypted, `00 07` packet 7, `01 64` battery 100 % (3.0 V and above), `02 4F 09` temperature
      0x094F = 23.83 °C, `03 22 10` humidity 0x1022 = 41.30 %, `0C BC 0B` voltage 0x0BBC = 3.004 V.
- [ ] The packet id increments every 10 s and the values match the UART log.
- [ ] RSSI with the phone at 1 m, in free space, in four board orientations. Expect roughly −45 to
      −65 dBm with the chip antenna. **Compare with a LaunchPad or the N54 board at the same spot**,
      since the absolute number depends heavily on the phone.
- [ ] Leave it running for at least an hour. With the LFOSC sleep clock, advertising must not stop
      and the UART must not show `critical error` or a reset.
- [ ] Optional: Home Assistant with the BTHome integration discovers the node automatically.

If nothing is seen on the phone while the UART log looks fine, suspect the RF path (C7/L1/C8/C6/L2/L3,
antenna feed) or HFXT accuracy (stage 6), not the firmware.

## Stage 5 — Current baseline

Purpose: catch hardware leakage early, before the real low-power work. Power **only** from the
bench supply or an ammeter in series with the cell. **Disconnect the USB-UART adapter and the probe**,
because both back-feed current through I/O pins.

Build without logging:

```sh
cd firmware/C23/ble_sensor
make clean && make EXTRA_CFLAGS=-DBSN_LOG_ENABLE=0 && make flash
```

Measure with the best tool available (Nordic PPK2, Joulescope, LP-XDS110ET EnergyTrace, or a DMM on the µA
range for averages only):

| Quantity | Datasheet reference | Rough expectation for this board |
|---|---|---|
| Standby floor between events | 0.71 µA (U1, LFOSC, DC/DC) + about 0.05 µA (HDC2010 sleep) | 1–3 µA. Clearly more points at leakage: flux, a cap, I/O contention |
| TX peak (0 dBm) | 5.1 mA | 5–7 mA spikes, three per advertising event |
| Average at 1 s advertising, 10 s sensor | | on the order of 10–20 µA |

Compare against the N54 board using the same method. For CR2032 lifetime estimates, see
`docs/datasheets/power/ti_coincell_peak_current_SWRA349.pdf` (peak-current derating) and the
Panasonic CR2032 datasheet. Later tuning knobs: advertising interval (`ble_sensor.syscfg`, `primIntMin/Max`),
`SENSOR_PERIOD_S` in `app_main.c`, TX power, and the HDC2010 resolution.

## Stage 6 — RF checks

1. **HFXT frequency offset.** BLE allows about ±50 ppm total, and the target is ±20 ppm or better (±49 kHz at 2.44 GHz).
   - Use TI **SmartRF Studio 8** (supports CC23xx over the XDS110) to send a continuous wave at 2440 MHz
     and read the carrier on a spectrum analyser or an SDR (e.g. HackRF, or a cheap RTL-SDR with an upconverter).
     SmartRF Studio loads its own firmware, so re-flash afterwards.
   - If the offset is consistently off across boards, set `CCFG.overrideHfxtCapArray = true` and tune
     `hfxtCapArrayQ1/Q2` in both `.syscfg` files: higher values mean more load capacitance, so a lower frequency.
2. **Range / RSSI vs distance** in an open corridor, side by side with the N54 board, both broadcasting at the
   same TX power.
3. **Antenna matching.** J1 (U.FL) and the C9/L4 path are DNP on rev A. Antenna impedance or VNA work
   needs a board reworked with J1 fitted. Record any rework in `hardware/C23/README.md` (board becomes `A*`).

---

## Results log

Copy one row per board.

| Board | S0 VDD–GND | S1 I (blank) | S1 VDDR / VDDD | S2 SWD | S3 hwtest | BLE address | S4 seen / RSSI@1m | S5 standby | S6 offset | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| #1 | | | | | | | | | | |
| #2 | | | | | | | | | | |

---

## Notes for rev B

Things found while writing the firmware that are cheap to fix in the next layout:

- **ROM UART bootloader pins.** The CC23xx ROM bootloader uses UART RX=DIO20 with TX=DIO6 (config 0)
  or RX=DIO12 with TX=DIO13 (config 1) (SWRA834, table 3-2). Rev A has TX=DIO13 and RX=DIO20, which match
  neither, and DIO6 is unconnected. Moving the board TX from DIO13 to DIO6, or adding a test point on DIO6,
  allows flashing over plain UART without an XDS110.
- **DIO21 doubles as the default bootloader trigger pin.** Harmless while the CCFG keeps pin triggering
  off, but worth knowing if the bootloader is ever enabled.
- **No LED.** A single LED on a spare DIO (DIO8 or DIO11), even DNP by default, would make bring-up and
  field debugging easier.
- **Test points are bare pads.** A Tag-Connect TC2030 footprint (SWD + VTREF + nRESET + UART TX) would
  make every flash a single plug instead of five pogo pins.

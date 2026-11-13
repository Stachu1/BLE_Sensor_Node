# BSN-C23-B bring-up and early test plan

Work through the stages in order. Each stage checks only what the previous one already proved, so the
first failure points at a small area of the board. Number the boards (#1, #2, ...) with a marker as you
assemble them, and fill in the [results table](#results-log) per board.

Tools, wiring and the `make` commands are described in [README.md](README.md). The procedure uses the rev B
reference designators and test points. The rev A version is at the tag `fw/BSN-C23-A`, and the rev A results
are kept below, marked rev A.

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

Rev B population reminder: **DNP** = C6 (100 µF), D1, R2 (LED), J1, J4 (2-pin headers). Everything else is
fitted. AE1 is the printed antenna, J3 is the Tag-Connect footprint.

- [ ] U1 (CC2340R5, QFN-24): pin-1 dot, no bridges on the 0.5 mm pitch, exposed pad soldered (check the side profile).
- [ ] U2 (HDC2010, 1.5 mm DSBGA): orientation (ball A1), sitting flat, and the sensor opening not
      covered in flux. **Don't wash the humidity sensor with IPA, and don't put flux on it**
      (see TI SNIA025). Reflow shifts RH by a few %RH, and it recovers after rehydration (roughly 24 h at room
      conditions, or longer at high RH).
- [ ] X1 (48 MHz, 4-pad): orientation per footprint.
- [ ] L4 (10 µH DC/DC inductor), C10–C13 near U1.
- [ ] RF path: C8, L1, C9 (pi network), C7 (DC block), J2 (MM8130), L2, L3 present and not tombstoned.
- [ ] R1 (0 Ω supply link) fitted.
- [ ] BT1 holder polarity.

With a DMM (no battery, no supply):

| Measurement | Expected | Typical fault if wrong |
|---|---|---|
| TP11 (VDD) to TP10 (GND) | Climbs slowly into the kΩ to MΩ range while C5 (100 µF) charges. **Not** < 100 Ω | Solder bridge, reversed cap, damaged U1 |
| C10 / C11 (VDDR) to GND | No short | Bridge at U1 pins 2/20, L4 |
| C13 (VDDD) to GND | No short | Bridge at U1 pin 16 |
| TP3 (SDA) to TP11, TP9 (SCL) to TP11 | about 4.7 kΩ | R5/R6 missing or wrong value |
| TP6 (nRESET) to TP11 | about 100 kΩ | R3 |
| TP1 (BOOT) to TP11 | about 100 kΩ | R4 |

## Stage 1 — First power with a blank chip

Use the bench supply on TP11/TP10 (or the battery-holder contacts), **with no coin cell fitted**.
Set it to **3.0 V and limit the current to 20 mA**.

- [ ] Supply current is steady and in the low single-digit mA range. The blank device sits in the ROM
      waiting for a valid image or bootloader command. If it hits the 20 mA limit, switch off and go back to stage 0.
- [ ] Nothing gets warm (fingertip on U1 and L4).
- [ ] VDD (TP11) = 3.0 V.
- [ ] VDDR (C10/C11 pad) is about 1.5 V.
- [ ] VDDD (C13 pad) is about 1.28 V.
- [ ] nRESET (TP6) and BOOT (TP1) are at VDD.

Record the currents. The same numbers on every board means good consistency. An outlier with
otherwise normal behaviour usually means leakage (flux residue, a part fitted that should be DNP).

## Stage 2 — SWD connection

Wire the XDS110 as in README.md (SWDIO→TP5, SWCLK→TP7, GND→TP10, VTREF→TP11, nRESET→TP6), or use a TC2030-NL
cable on J3. Keep powering from the bench supply.

```sh
cd firmware/C23/hwtest
make probe      # the XDS110 must be listed
make erase      # first real conversation with the chip
```

**With a SEGGER J-Link** (e.g. J-Link PLUS Compact, 0.05" 9-pin Cortex-M connector):

| J-Link pin | Signal | Board |
|---|---|---|
| 1 | VTref (sense only, doesn't power the board) | TP11 |
| 2 | SWDIO | TP5 |
| 3 or 5 | GND | TP10 |
| 4 | SWCLK | TP7 |
| 10 | nRESET (optional) | TP6 |

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

Connect the USB-UART adapter: **adapter RX → TP2**, GND → TP10. Leave TP8 unconnected. Open a terminal
(PuTTY is installed) on the adapter's COM port at **115200 8N1**, then:

```sh
cd firmware/C23/hwtest
make flash
```

The board starts after programming. Expected output (from rev A board #1 with the rev B names, your address,
part ID and readings will differ):

```
==== BSN-C23-B hwtest 0.1.0 (built Oct 22 2026 14:00:00) ====
Reset reason : SWD (debugger)
BLE address  : XX:XX:XX:XX:XX:XX
Part ID      : 0x.......
[PASS] HFXT 48 MHz (X1)
[PASS] LF clock (LFOSC)
[PASS] VDDS                   3004 mV
Die temp     : 24 C
[PASS] I2C open
I2C scan     : 0x40
[PASS] HDC2010 ID (U2 @0x40) manuf 0x5449 dev 0x07D0
[PASS] HDC2010 config
[PASS] HDC INT idle low
[PASS] HDC2010 trigger
[PASS] HDC INT level (DIO13)
[PASS] HDC INT edge IRQ
[PASS] HDC2010 DRDY status
[PASS] HDC INT cleared
[PASS] HDC2010 plausible      23.84 C  41.27 %RH
[INFO] SHTC3 (U2 @0x70)       not present (not on rev B)
==== Self-test: 13 passed, 0 failed -> PASS ====

#0 VDDS=3004 mV die=24 C | HDC2010 23.86 C 41.20 %RH | INT edges=2
#1 VDDS=3004 mV die=24 C | HDC2010 23.85 C 41.22 %RH | INT edges=3
```

Record the **BLE address** for each board. Stage 4 uses it.

Then check that the readings respond to the environment:

- [ ] Breathe on U2: RH jumps by 10–30 %RH and temperature rises within a few seconds, then both recover.
- [ ] HDC2010 temperature is within about 1 °C of a reference thermometer. It may read a little high
      from board self-heating while the UART is printing.
- [ ] Die temperature (±few °C resolution) roughly agrees with the HDC2010.
- [ ] Short TP6 to GND briefly: the board restarts and prints `Reset reason : reset pin`.
- [ ] Power-cycle from the supply: `Reset reason : power-on`.

If any check FAILs:

| FAIL | Likely cause |
|---|---|
| No output at all | Adapter RX on the wrong test point, wrong COM port or baud rate, TX/RX swapped at the adapter. Use the CCS debugger to see if `main` runs. |
| `HFXT 48 MHz` | X1 orientation or soldering, X1 is the wrong part, a broken trace to U1 pins 21/22 |
| `LF clock` | Shouldn't happen with LFOSC. Check that the image was built from this repo (CCFG `srcClkLF`). |
| `VDDS` out of range | Supply setting, or batteries below 1.8 V |
| `I2C scan: none` | R5/R6, SDA/SCL bridged, U2 not soldered or rotated, U2 without VDD (ball A1) |
| `HDC2010 ID` with other addresses found | Wrong part fitted, or ADDR (ball B1) not at GND, which moves the device to 0x41 |
| `HDC INT level` FAIL but ID PASS | Open trace between U2 ball C2 and U1 pin 6 (DIO13). Probe TP4 with a scope while it runs |
| `HDC2010 plausible` | Sensor damaged or contaminated, or the formula is off. Compare with a reference sensor |

## Stage 4 — BLE firmware (`ble_sensor`)

```sh
cd firmware/C23/ble_sensor
make flash
```

UART output:

```
==== BSN-C23-B ble_sensor 0.1.0 (built ...) ====
[SNS] HDC2010 ok
[BLE] stack ready, address 0xXXXXXXXXXXXX (same as in hwtest)
[BLE] advertising started (interval 1000 ms)
[SNS] #1 23.91 C 41.30 %RH VDDS 3004 mV
[SNS] #2 ...
```

With a J-Link, `make jflash` stops after programming. Unplug the J-Link USB, power the board off for
at least 30 s, then power it on. SEGGER's post-flash reset left the core halted in the ROM on rev A board #1.

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
- [ ] RSSI with the phone at 1 m, in free space, in four board orientations. On rev A (chip antenna) the
      rough expectation was −45 to −65 dBm. **Compare with a LaunchPad or the N54 board at the same spot**,
      since the absolute number depends heavily on the phone.
- [ ] Leave it running for at least an hour. With the LFOSC sleep clock, advertising must not stop
      and the UART must not show `critical error` or a reset.
- [ ] Optional: Home Assistant with the BTHome integration discovers the node automatically.

> **Rev B antenna match.** L2 = 1.6 nH and L3 = 6.8 nH come from the openEMS simulation
> (`hardware/C23/testing/RF/antenna_C23-B/README.md`) and have not been measured. Check S11 at J2 (stage 6)
> before trusting RSSI numbers. On rev A the TI reference values were about three times off
> (`hardware/C23/testing/rev_A/RF/ANTENNA_MATCHING.md`).

If nothing is seen on the phone while the UART log looks fine, suspect the RF path (C8/L1/C9/C7/J2/L2/L3,
antenna feed) or HFXT accuracy (stage 6), not the firmware.

## Stage 5 — Current baseline

Purpose: catch hardware leakage early, before the real low-power work. Power **only** from the
bench supply or an ammeter in series with the cell. **Disconnect the USB-UART adapter and the probe**,
because both back-feed current through I/O pins.

Build without logging:

```sh
cd firmware/C23/ble_sensor
make LOG=0 && make flash
```

Measure with the best tool available (Nordic PPK2, Joulescope, LP-XDS110ET EnergyTrace, or a DMM on the µA
range for averages only):

| Quantity | Datasheet reference | Rough expectation for this board |
|---|---|---|
| Standby floor between events | 0.71 µA (U1, LFOSC, DC/DC) + about 0.05 µA (HDC2010 sleep) | 1–3 µA. Clearly more points at leakage: flux, a cap, I/O contention |
| TX peak (0 dBm) | 5.1 mA | 5–7 mA spikes, three per advertising event |
| Average at 1 s advertising, 10 s sensor | | on the order of 10–20 µA |

Compare against the N54 board using the same method. For CR2032 lifetime estimates, see
TI [SWRA349](https://www.ti.com/lit/pdf/swra349) (peak-current derating) and the
Panasonic CR2032 datasheet. Later tuning knobs: advertising interval (`ble_sensor.syscfg`, `primIntMin/Max`),
`SENSOR_PERIOD_S` in `app_main.c`, TX power, and the HDC2010 resolution.

## Stage 6 — RF checks

1. **HFXT frequency offset.** BLE allows about ±50 ppm total, and the target is ±20 ppm or better (±49 kHz at 2.44 GHz).
   - Use TI **SmartRF Studio 8** (supports CC23xx over the XDS110) to send a continuous wave at 2440 MHz
     and read the carrier on a spectrum analyser or an SDR (e.g. HackRF, or a cheap RTL-SDR with an upconverter).
     SmartRF Studio loads its own firmware, so re-flash afterwards.
   - If the offset is consistently off across boards, set `CCFG.overrideHfxtCapArray = true` and tune
     `hfxtCapArrayQ1/Q2` in both `.syscfg` files: higher values mean more load capacitance, so a lower frequency.
   - Without a spectrum analyser, a VNA works as a receiver: trace `A,2` (port 1 receiver, source port 2,
     RF power off), span 1–10 MHz around the carrier. Setup and caveats are in `hardware/C23/testing/rev_A/RF/RF_CARRIER.md`.
   - [x] Rev A, 2026-10-26, `cwtest` on an MCU-only board: factory trim (35) +30.3 ppm, trim 44 +2.2 ppm.
         Q1 = Q2 = 44 is now set in both `.syscfg` files (about 3 ppm per step). Output at the U.FL: −2.1 dBm at
         the 0 dBm setting, +6.7 dBm at +8 dBm.
   - [ ] Rev B: check the offset with trim 44 on a second board (design offset or crystal spread).
2. **Range / RSSI vs distance** in an open corridor, side by side with the N54 board, both broadcasting at the
   same TX power.
3. **Antenna matching.** On rev B, plug the MM8130 probe (MXHS83QE3000) into J2. It disconnects the chip side,
   so the VNA sees the antenna with L2 and L3. Measure with the board lifted or hanging, not flat on a bench.
   Record any part change in `hardware/C23/README.md` (board becomes `B*`).
   - [ ] Rev B: S11 at J2 with the simulated parts (L2 1.6 nH, L3 6.8 nH), then retune if needed.
   - Rev A (J1 U.FL fitted by rework):
   - [x] Antenna side matched flat on a wooden table (2026-10-23): L2 3.3 nH, L3 pads 2.0 pF,
         S11 < −11 dB in band. The table detuned the antenna, so these values don't apply. See
         `hardware/C23/testing/rev_A/RF/ANTENNA_MATCHING.md`.
   - [x] Re-match with the board lifted (2026-10-26): L2 4.3 nH, L3 pads 2.1 pF,
         −32 dB at 2.44 GHz, S11 < −10 dB in band.
   - [ ] Rev A: fit the final values on a working board and compare RSSI with the reference values.
   - Do this before the range test in step 2, otherwise the range data compares an untuned C23 against the N54.

---

## Results log

Copy one row per board. Rev A boards are marked A.

| Board | S0 VDD–GND | S1 I (blank) | S1 VDDR / VDDD | S2 SWD | S3 hwtest | BLE address | S4 seen / RSSI@1m | S5 standby | S6 offset | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| A #1 | No shorts (diode mode) | ~4 mA steady | | PASS | 13/13 PASS | FC:DE:C5:73:2F:4E | Seen (`bsn_scan.py`) / not measured | 0.366 µA (`pwrtest`, U2 fitted) | | Antenna matched (A\*). J-Link: needs a power cycle after `jflash` (see stage 4). |
| B #1 | | | | | | | | | | |
| B #2 | | 4 mA at 3.0 V | | PASS (J-Link on J3, Tag-Connect) | 13/13 PASS (2026-11-13, RAM log build) | FC:DE:C5:73:2F:5A | Seen (`bsn_scan.py`, 2026-11-13, `LOG=1 DRDY=7 SAFE=0`), BTHome decoded, about 4.8 adverts/s by the packet counter / −51 to −57 dBm at the laptop on the bench, distance not measured, simulated match values | | | One 100 µF cap, J2 to the antenna, matching network fitted. UART TX on TP2 not checked yet. |

---

## Notes for rev B

Things found while writing the firmware that are cheap to fix in the next layout. All four are done on rev B
(see [`hardware/C23/README.md`](../../hardware/C23/README.md#rev-b-bsn-c23-b)).

- **ROM UART bootloader pins.** The CC23xx ROM bootloader uses UART RX=DIO20 with TX=DIO6 (config 0)
  or RX=DIO12 with TX=DIO13 (config 1) (SWRA834, table 3-2). Rev A has TX=DIO13 and RX=DIO20, which match
  neither, and DIO6 is unconnected. Moving the board TX from DIO13 to DIO6, or adding a test point on DIO6,
  allows flashing over plain UART without an XDS110.
  **Done on rev B:** TX on DIO6 (TP2), and a BOOT pin on DIO3 (TP1) with a 100 kΩ pull-up as the trigger.
- **DIO21 doubles as the default bootloader trigger pin.** Harmless while the CCFG keeps pin triggering
  off, but worth knowing if the bootloader is ever enabled.
  **Done on rev B:** HDC2010 INT moved to DIO13, DIO21 is unused.
- **No LED.** A single LED on a spare DIO (DIO8 or DIO11), even DNP by default, would make bring-up and
  field debugging easier.
  **Done on rev B:** D1 with R2 1 kΩ on DIO4, DNP by default.
- **Test points are bare pads.** A Tag-Connect TC2030 footprint (SWD + VTREF + nRESET + UART TX) would
  make every flash a single plug instead of five pogo pins.
  **Done on rev B:** TC2030-NL footprint J3 with SWD, VTREF and nRESET. UART TX stays on TP2.

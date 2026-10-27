# BSN-N54-A bring-up and early test plan

Same stages as [`firmware/C23/BRINGUP.md`](../C23/BRINGUP.md), cut down to what the MCU comparison needs. Number
the boards (#1, #2, ...) with a marker and fill in the [results table](#results-log).

Tools and `make` commands: [README.md](README.md).

## Assembly configurations

Three builds, matching the C23 boards:

| Build | Fit | Leave off | Used for |
|---|---|---|---|
| **Full** | Everything in `hardware/N54/BSN-N54.csv` | J1, R4 (unless you also want U.FL access) | `hwtest`, `ble_sensor`, `pwrtest` |
| **MCU + U.FL (conducted)** | U1, X1, X2, power parts (L1, C1–C13, FB1), L2, C14, L3, C15, L4, C16, **R4 0 Ω**, **J1** | L5, L6, L7, AE1 | `cwtest`: output power, frequency offset, harmonics |
| **Antenna + match** | J1, R4 0 Ω, L6, L7, AE1 (battery connector BT1 fitted, as on C23) | U1 side: L2–L4, C14–C16, L5 | VNA S11 of the antenna branch |

RF network as drawn in the schematic:

```
U1.ANT(31) ─ L2 ─┬─ L3 ─┬─ L4 ─┬──────────── L6 ─┬─ AE1
                C14    C15    C16   L5      │     L7
                 │      │      │    │      R4     │
                GND    GND    GND  GND      │    GND
                                            J1
```

L5 (7.3 nH) is a **shunt to GND on the J1 node** (the first version of the diagram in `hardware/N54/README.md`
drew it in series). L7 is a shunt at the antenna feed. For the conducted build, leaving L5 off gives the
PA network (L2–L4, C14–C16) straight into 50 Ω. L5 is about j112 Ω at 2.44 GHz, so it belongs to the
antenna-side match and stays off for conducted measurements.

**Rev A result:** the PA network as laid out (0402) loses 10–11 dB into 50 Ω. Board #2 runs with it bypassed (15 pF
in series at L2, L3/L4 bridged, C14–C16 off) and then gives the datasheet power. See
[`hardware/N54/testing/RF/RF_CARRIER.md`](../../hardware/N54/testing/RF/RF_CARRIER.md).

## Stage 0 — Visual and ohmmeter (unpowered)

- [ ] U1 (QFN-48, 0.4 mm pitch): pin-1 mark, no bridges, exposed pad soldered.
- [ ] U3 (HDC2010) orientation, no flux on the sensor opening. U2 (SHTC3) orientation.
- [ ] X1 (32 MHz, 4-pad) and X2 (32.768 kHz) fitted.
- [ ] L1 (4.7 µH, DC/DC) and the DECD/DECA decoupling (C6–C9, FB1).
- [ ] TP1 (VDD) to TP4 (GND): no short (C10 100 µF charges slowly).
- [ ] TP6 (SDA) and TP7 (SCL) to TP1: about 4.7 kΩ.

## Stage 1 — First power

Bench supply on TP1/TP4, **3.0 V, current limit 20 mA**, no coin cell. Raise the limit to at least
40 mA before running `cwtest` at +8 dBm. With the rev A PA network fitted the board averaged about 18 mA there
(about 13 mA with the network bypassed), and at 20 mA the peaks browned it out, so the carrier flickered on and off.

- [ ] Steady current, nothing warm. A blank nRF54L sits in a few hundred µA to a few mA.
- [ ] VDD = 3.0 V at TP1.

## Stage 2 — SWD connection

| J-Link pin | Signal | Board |
|---|---|---|
| 1 | VTref | TP1 (VDD) |
| 2 | SWDIO | TP3 |
| 4 | SWCLK | TP2 |
| 3 or 5 | GND | TP4 |

TP5 is nRESET (pin 10 on the J-Link). Leave it unconnected: SWD resets the chip by itself.

```sh
cd firmware/N54/hwtest
make recover        # first contact: erases the chip and lifts the access-port protection
```

- [ ] `make recover` completes. If it fails, check the wiring, VTref, and the U1 pins 25/26 solder joints.

## Stage 3 — `hwtest`

USB-UART adapter **RX → TP9**, GND → TP4. Leave TP10 unconnected. 115200 8N1.

```sh
make flash
```

Without a USB-UART adapter, send the log over the J-Link instead:

```sh
make flash RTT=1
sh ../tools/rtt_log.sh      # prints the log; start it before powering the board to see the boot lines
```

`hwtest` runs straight after flashing. Other images (`ble_sensor`, `cwtest`, `pwrtest`) stay stuck after the
post-flash reset until a power-on reset: power off, short TP1 to TP4 for about 1 s, power on. The first VDD
reading after power-on reads low (2.2–2.4 V at 3.0 V) on both boards; later readings are correct.

Expected (address and readings differ):

```
==== BSN-N54-A hwtest 0.1.0 (built ...) ====
Reset reason : ...
BLE address  : XX:XX:XX:XX:XX:XX
Part         : 0x........ variant 0x........
[PASS] HFXO 32 MHz (X1)       started in ... us
[PASS] LFRC 32.768 kHz        source LFRC
[PASS] VDD                    3000 mV
Die temp     : 24 C
[PASS] I2C ready (i2c30)
I2C scan     : 0x40 0x70
[PASS] HDC2010 ID (U3 @0x40)  manuf 0x5449 dev 0x07D0
...
[PASS] SHTC3 ID (U2 @0x70)    ID 0x....
[PASS] SHTC3 plausible        ...
==== Self-test: N passed, 0 failed -> PASS ====
```

| FAIL | Likely cause |
|---|---|
| No output | Adapter RX not on TP9, wrong COM port, image not running (try `make flash` again) |
| `HFXO` | X1 soldering or orientation, wrong load capacitance in `common/bsn_n54.overlay` |
| `LFXO` source `LFRC` or error (`LFCLK=xtal` builds) | X2 soldering; the clock driver falls back to RC if the crystal doesn't start |
| `I2C scan: none` | R2/R3, SDA/SCL bridged, U3/U2 not soldered |
| `HDC INT level` | Open trace between U3 ball C2 and P0.01 (TP8) |

Record the **BLE address**.

## Stage 4 — `ble_sensor`

```sh
cd ../ble_sensor
make flash
python ../../C23/tools/bsn_scan.py --mac <address from stage 3>
```

- [ ] A device named **BSN-N54** advertises BTHome (UUID 0xFCD2), and the values match the UART log.

## Stage 5 — Current (for the MCU comparison)

Same meter, ranges and procedure as [`POWER_MEASUREMENTS.md`](../../hardware/C23/testing/Power/POWER_MEASUREMENTS.md).
After flashing, unplug the J-Link and short TP1 to TP4 for about 1 s.

| Measurement | Build | N54 board #2 | C23 result for comparison |
|---|---|---|---|
| Sleep floor | `pwrtest` `make flash MODE=standby` | 4.16 µA | 0.366 µA |
| Floor with the BLE stack idle | `ble_sensor` `make flash LOG=0 SENSOR_S=0 ADV=0` | | 0.367 µA |
| Advertising charge at 0 dBm | `ble_sensor` `make flash LOG=0 SENSOR_S=0 ADV_MS=50` and `ADV_MS=100` | 7.6 µC | 12.6 µC |
| Advertising charge at +8 dBm | the same with `TX_DBM=8` | | 27.3 µC |
| Sensor reading, polled | `pwrtest` `make flash MODE=sensor PERIOD_MS=97` | | 9.56 µC |
| System OFF floor | `pwrtest` `make flash MODE=shutdown` | 2.05 µA | (C23 unresolved) |

`Q_adv = (I_avg − I_floor) × (ADV_MS + 5 ms)`. Terminate J1 with 50 Ω on a conducted board, so the PA sees the load
the datasheet assumes. Full notes: [`hardware/N54/testing/Power/POWER_MEASUREMENTS.md`](../../hardware/N54/testing/Power/POWER_MEASUREMENTS.md).

## Stage 6 — RF (conducted build)

```sh
cd ../cwtest
make flash                    # 2440 MHz, 0 dBm
make flash TX_DBM=8
```

Power-cycle after flashing, disconnect the probe and UART, then measure output power, frequency offset and
harmonics at J1 exactly as for C23 ([`RF_CARRIER.md`](../../hardware/C23/testing/RF/RF_CARRIER.md)).

---

## Results log

| Board | Build | S1 I | S2 SWD | S3 hwtest | BLE address | S4 seen | S5 floor | S5 Q_adv 0 dBm | S6 power @0/+8 dBm | S6 offset | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| #1 | Full (no U2, X2) | ~2 mA | PASS | 13/13 PASS | EC:A6:80:CE:7A:1A | Seen (`bsn_scan.py`) | | | | | PA network as designed (−10 dB). Antenna side with the C23 values, not verified |
| #2 | MCU + U.FL (no U2, X2) | | PASS | 13/13 PASS | FA:28:B5:E0:85:F5 | (no antenna) | 4.16 µA (OFF 2.05 µA) | 7.6 µC | 0.0 / +7.5 dBm (network bypassed) | ≈ 0 at 11.75 pF | A\*: PA network bypassed. +127 ppm at 7 pF |

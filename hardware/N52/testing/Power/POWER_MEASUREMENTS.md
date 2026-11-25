# BSN-N52-A current measurements

Average current at the 5 s DRDY interval (T1) on `BSN-N52-A`. Moved here from the AirTag bring-up notes
(2026-11-23). Firmware: [`firmware/N52`](../../../../firmware/N52).

## Session 2026-11-23, A #3

A #3 (BLE address `DB:1C:AA:DB:F2:9D`), 0 dBm, HDC2010 in auto mode at 0.2 Hz (one advert per DRDY, nominal 5 s).

- **Meter:** bench DMM, 100 PLC, autozero on, **10 mA range**.
- **Supply:** board powered from the bench supply (voltage not recorded), J-Link unplugged, board power-cycled
  after flashing. After any SWD access the nRF52 only emulates System OFF and draws more, so the power cycle is
  needed.
- At the time the firmware advertised the name `BSN-52`. It is now `BSN-N52`, one byte longer, which adds about
  8 µs of air time per channel. That is negligible here.

| # | Firmware | Mean | σ | n | SEM |
|---|---|---|---|---|---|
| N1 | `ble_sensor` (Zephyr + BLE controller, System ON idle between adverts) | 12.765 µA | 3.3 µA | 150 | 0.27 µA |
| N2 | `ble_beacon_min` (bare metal, System OFF between adverts) | **1.706 µA** | 1.985 µA | 685 | 0.076 µA |

- **`ble_beacon_min` is 7.5 times lower than `ble_sensor`.** With Zephyr the SoC stays in System ON idle: the
  BLE controller keeps the LFRC and RTC running and wakes the HFXO every 4 s for the RC calibration. The bare-metal
  build has no timebase at all. The HDC2010's DRDY interrupt is the only wake source, and each wake is a reset out
  of System OFF.
- **Against `BSN-C23-B` at the same 5 s interval:** 4.357 ± 0.141 µA (B #1) and 4.391 ± 0.149 µA (B #2), see
  [`../../../C23/testing/rev_B/Power/POWER_MEASUREMENTS.md`](../../../C23/testing/rev_B/Power/POWER_MEASUREMENTS.md).
  N2 is about **2.5 times lower**.
- The large σ is the 5 s burst pattern seen through 100 PLC windows (a window either holds an advert or not), the
  same effect as on the C23.

### Caveats

- **Single reading on the 10 mA range.** The DMM's offset error on that range is of the order of the result, so
  the absolute value needs a check on a lower range (the C23 floor was read on 1 mA) or with a PPK2.
- The DRDY period of A #3 was not measured. On the C23 soak nodes the HDC2010 timer gave 4.81 to 5.34 s (about
  ±5 %), so the average current at exactly 5 s can differ by the same amount.
- One board only. No floor reading (System OFF without wakes) and no charge per event yet, so there is no model
  to compare against as on the C23.
- The two variants are not the same comparison as N54 against C23 on rev A. The N52 build has no BLE stack, no
  connections and no advertising delay (the timing comes only from the HDC2010). The C23 runs the full TI stack.

### Rough battery life, before derating

Nominal capacities, no self-discharge, no pulse or temperature derating:

| | Average | Cell | Life |
|---|---|---|---|
| `BSN-N52-A`, `ble_beacon_min` | 1.706 µA | CR1632, about 130 mAh | about 8.7 years |
| `BSN-C23-B` | 4.37 µA | CR2032, about 225 mAh | about 5.9 years |

At these currents self-discharge (about 1 % a year) and the cell's shelf life matter as much as the load, so
these numbers are an upper bound, not a projection.

## Session 2026-11-25, A #3: floor, charge per event, 5 s repeat

Same board (device ID `47a70671fbe71ff6`), `ble_beacon_min`, 0 dBm, bench supply at 3.005 V, J-Link unplugged
and the board power-cycled after every flash. Meter: same DMM, 100 PLC, autozero on. Board identity read over SWD
before each flash.

| # | Build | Range | Mean | σ | n | SEM | Event period |
|---|---|---|---|---|---|---|---|
| N3 (N-T1b) | `make DRDY=0` (one advert at power-up, then System OFF for good) | 100 µA | **0.323 µA** | 0.026 µA | 352 | 0.001 µA | – |
| N4 (N-T1d) | `make DRDY=7` (0.2 s) | 10 mA | **40.95 µA** | 3.64 µA | 270 | 0.22 µA | 210.9 ± 0.6 ms |
| N5 (N2 repeat) | `make DRDY=4` (5 s) | 10 mA | **1.771 µA** | 2.027 µA | 1525 | 0.052 µA | 5.268 ± 0.006 s |

- **Periods** from the packet id against time on the NINA (`bsn_scan_nina.py --mac DB:1C:AA:DB:F2:9D`), id
  unwrapped (8 bits), least-squares fit, error from the 1 s timestamps over the span:
  [`a3_drdy7.csv`](a3_drdy7.csv) (360 s, 1705 ids, 556 received) and [`a3_drdy4.csv`](a3_drdy4.csv) (880 s, 168
  ids, 62 received). Both periods are about 5.4 % longer than nominal, so the HDC2010 timer on this board runs
  slow by about the same factor at both rates.
- **Charge per event:** Q = (N4 − N3) × 0.2109 s = **8.57 ± 0.05 µC**. C23-B: 21.3 µC (B #1), so about 2.5 times
  less per event.
- **Model at the measured 5.268 s:** 0.323 + 8.57 / 5.268 = **1.950 µA**. At exactly 5 s: 2.037 µA.
- **N5 is 9 % below the model** (1.771 against 1.950 µA, about 3.4 SEM). The C23-B also measured 5 to 11 % below
  its model with the same method. Cause not investigated. Candidates: the charge per event is not the same at
  0.2 s and at 5 s, or the 10 mA range offset (N4 and N5 are both on it, the floor is not).
- **N5 agrees with N2** (1.771 ± 0.052 against 1.706 ± 0.076 µA, within 1σ of the combined error). The 23 Nov
  reading stands, now with the period known.
- The NINA received only 33 % (0.2 s) and 37 % (5 s) of the ids. That does not affect the period fit. The C23
  nodes near the module lost 13 to 18 %. Cause not investigated.

## Open (if there is time)

- A second board.
- The model gap (above), shared with the C23.

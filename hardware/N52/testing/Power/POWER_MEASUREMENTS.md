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

## Open (if there is time)

- Floor: System OFF with the HDC2010 stopped (or INT not wired), on the 1 mA range.
- Charge per event: `ble_beacon_min` at a faster DRDY rate (0.2 s, as `DRDY=7` on the C23), then the model at 5 s.
- The DRDY period of the measured board from the packet id on the NINA scanner.
- A second board.

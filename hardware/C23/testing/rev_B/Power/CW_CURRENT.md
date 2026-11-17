# BSN-C23-B continuous-wave supply current (chamber budget)

B #3 running `cwtest` (unmodulated carrier, `firmware/C23/cwtest`), measured 2026-11-17 at the uni power lab
right after the spectrum analyser session. This is the steady draw in CW mode, used to decide the battery and
the session length for a radiated chamber run. It is not the sleep/advertising power model (that is in
[`../../rev_A/Power/POWER_MEASUREMENTS.md`](../../rev_A/Power/POWER_MEASUREMENTS.md) and the rev B T1/T2 work).

## Result

| TX setting | Mean current | Stddev | Samples |
|---|---|---|---|
| 0 dBm | 6.135 mA | 24 µA | 135 |
| +4 dBm | 10.902 mA | 38 µA | 120 |
| +8 dBm | 14.203 mA | ~130 µA | 295 |

- Carrier 2440 MHz, B #3 (two 100 µF caps, J2 to the PA), probe not connected (radiating from the antenna).
- Supply **3.0 V from a bench PSU** (not the AA cells, not the DC-DC input from a cell). The node runs from the
  DC-DC internally.
- The +8 dBm stddev as first logged was 231 µA, inflated by a finger brought to the antenna several times during
  the reading (see below). The settled value is about 130 µA, in line with the other settings.

## Notes

- **Finger on the antenna drops the current.** Bringing a finger near the antenna detunes it, which changes the
  load the PA drives, and the supply current falls (from about 14.2 mA toward about 13 mA while touched). It is a
  measurement artefact here, but it confirms the antenna is radiating and that a hand nearby shifts the match.
  Relevant to how the node is held in the range test and the chamber.
- **PA efficiency is low.** At +8 dBm: 14.2 mA × 3.0 V ≈ 43 mW in, for +2.4 dBm (1.7 mW) conducted at J2 (probe
  and cable loss not corrected, so the true radiated power is somewhat higher). Normal for this PA.

## CR2032 voltage under CW load (2026-11-17)

Cell: RS Pro (marking "NL"), no-brand, considered low quality. Each cell fresh. Board on the cell through the
header jumper, carrier on the whole time. The "caps charged" row is the open-circuit voltage before the carrier
starts.

### +8 dBm (14.2 mA)

| Time | Voltage |
|---|---|
| caps charged, no load | 3.282 V |
| 0 min (carrier on) | 2.950 V |
| 3 min | 2.744 V |
| 6 min | 2.650 V |
| 9 min | 2.599 V |
| 12 min | 2.575 V |
| 15 min | 2.563 V |

Recovery after unplugging the load at 15 min: 2.80 V at ~1 min, 2.868 V at 3 min, 2.898 V at 6 min, 2.937 V at
15 min, still slowly rising. It does not return to 3.282 V, so the sag is mostly IR drop across the cell's
internal resistance relaxing, with some real capacity used.

- Instant IR drop at switch-on: (3.282 − 2.950) / 14.2 mA ≈ 23 Ω.
- Apparent resistance at 15 min: (3.282 − 2.563) / 14.2 mA ≈ 51 Ω.

The curve is flattening toward about 2.55 V (drops of 51, 24, 12 mV over the last three steps). The board keeps
running (it is fed from the DC-DC), but a no-brand coin cell at 14 mA is clearly stressed.

### 0 dBm (6.1 mA)

Fresh cell, same RS "NL" type.

| Time | Voltage |
|---|---|
| caps charged, no load | 3.286 V |
| 0 min (carrier on) | 3.170 V |
| 3 min | 2.912 V |
| 6 min | 2.855 V |
| 9.5 min | 2.807 V |
| 12 min | 2.781 V |
| 15 min | 2.762 V |

Recovery after unplugging the load at 15 min: 2.898 V at 1.5 min, 2.918 V at 3 min, 2.939 V at 6 min, 2.970 V at
15 min.

- Instant IR drop at switch-on: (3.286 − 3.170) / 6.1 mA ≈ 19 Ω, close to the 23 Ω seen at +8 dBm, so the cell's
  internal resistance is consistent between the two runs.
- The 0 dBm curve settles about 0.20 V higher than the +8 dBm curve at every point (2.762 V against 2.563 V at
  15 min) and is still slowly falling, flattening toward roughly 2.74 V.

Both cells recover to about 2.9 V unloaded, not to 3.28 V, so a good part of the sag is the cell relaxing (IR
and polarisation), with some real capacity used. A quality cell (Duracell) would sag less.

### Comparison plot

[`voltage_hold.png`](voltage_hold.png) (from `voltage_hold.py`): the two hold curves and their recoveries, with
a dot on each measured point so it is clear only a few samples were taken.

## Chamber budget

**Decision (2026-11-17): run the chamber at 0 dBm on an on-board CR2032.** The node ships at 0 dBm (the BLE stack
default, what `ble_sensor` transmits), so 0 dBm is the real radiated pattern, efficiency and compliance case. The
+8 dBm CW runs today were a worst-case probe for power and harmonics, not the operating point. At 0 dBm the node
draws 6.1 mA, not 14.2, so the IR drop on this cell is about 0.14 V instead of 0.33 V and a coin cell is
plausible for a few-hour run. An on-board coin cell also avoids a holder and cable near the antenna, which would
radiate and distort the pattern (the ferrite question put to Kasper). Confirm with the 0 dBm hold test above.

For the report: note the cell voltage at the start and end of the chamber run. If it sags during a multi-hour
run the TX power drifts slightly, which is fine for a relative pattern but matters for an absolute efficiency
number. A quality cell (Duracell) would sag less than this RS no-brand.

## Open

- [ ] 0 dBm CR2032 voltage-hold over 15 min, to confirm a coin cell survives a chamber session at the operating
      power.
- [ ] Repeat the +8 dBm current reading without touching the antenna, to pin the settled stddev.

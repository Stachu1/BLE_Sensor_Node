# BSN-N54-A carrier frequency and output power (2026-10-27)

Checking the HFXO frequency offset and the TX output power on board #2 with the `cwtest` firmware
(`firmware/N54/cwtest`, carrier at 2440 MHz), measured with the Keysight P9370B VNA used as a receiver, the same
setup as [`hardware/C23/testing/RF/RF_CARRIER.md`](../../../C23/testing/RF/RF_CARRIER.md).

**Results:**

- **HFXO:** with the datasheet load capacitance of X1 (7 pF) the carrier was **+127 ppm** high. **11.75 pF** of
  internal load capacitance brings it to within a few kHz. This is now the default in `firmware/N54/common/bsn_n54.overlay`.
- **Output power:** with the Nordic reference PA network fitted (L2/C14/L3/C15/L4/C16), the output at J1 was
  **10–11 dB** below the PA setting. With the network bypassed, the PA delivers its datasheet power into 50 Ω:
  **0.0 dBm at the 0 dBm setting** and **+7.5 dBm at +8 dBm**.

## Test board

Board #2: MCU, X1 (no X2), power parts, the PA network, R4 (0 Ω) and J1 (U.FL), no antenna. J1 goes to VNA
port 1. Bench supply at 3.0 V on TP1/TP4. The board was later reworked to bypass the PA network (see below and the
rework log in [`hardware/N54/README.md`](../../README.md)).

## VNA setup

As for C23: trace `A,2` (receiver A with source port 2, RF power off), +0.67 dB thru correction, carrier frequency
taken as the centre of the peak's −6 dB width. The levels below are as read. The offsets come from the same method.

## Frequency offset and crystal trim

| `HFXO_CL_FF` | `INTCAP` register | Carrier offset | |
|---|---|---|---|
| 7000 (X1 datasheet CL) | 14 | **+310 kHz (+127 ppm)** | `PATTERN=0` |
| 7000 | 14 | tone at +560 kHz | `PATTERN=1` (all-1 packets: carrier + deviation) |
| 7000 | 14 | tone at +60 kHz | `PATTERN=2` (all-0 packets: carrier − deviation) |
| 17000 (maximum) | | −176 kHz (−72 ppm) | 2439.8238 MHz |
| 11500 | | +20 kHz (+8 ppm) | |
| 12000 | 32 | −10 kHz (−4 ppm) | 2439.99 MHz |
| **11750** | | **≈ 0 (within a few kHz)** | at 0 dBm, and about +6 kHz at +8 dBm |

How the offset was checked:

1. The first reading (+310 kHz) looked too large for a crystal error, so `cwtest` got a `PATTERN` option that sends
   the two BLE FSK tones on their own. Their midpoint (+310 kHz) and spacing (500 kHz, ±250 kHz deviation) confirm
   that the TXIDLE carrier is centred and the offset is real.
2. The C23 CW board re-measured on the same setup read +9 kHz (+5.3 kHz the day before), so the VNA is not the cause.
3. The internal load capacitor register `OSCILLATORS.XOSC32M.CONFIG.INTCAP` was read over the J-Link: 14 at 7 pF,
   which is what Nordic's formula with this chip's `FICR.XOSC32MTRIM` gives, so the setting is applied.
4. Reflowing X1 changed nothing. The crystal is marked "32" and responds normally to the load: about 200 ppm over
   7 → 17 pF, about 4–5 ppm per 250 fF step near 11.75 pF.

**Why so far off at 7 pF** is not settled. The X1 datasheet gives CL = 7.0 pF and ±10 ppm, and C23 also needed
more load than its factory trim (cap array 35 → 44, +30 → +2 ppm). Check board #1 at 11.75 pF to see how much of
this is board-to-board spread.

## Output power

All at the U.FL, VNA receiver, as read. Supply current from the bench PSU display (not precise).

| PA network | Setting | Output | Supply current |
|---|---|---|---|
| Nordic reference (L2 2.7 nH, C14 1.5 pF, L3 3.5 nH, C15 2.0 pF, L4 3.5 nH, C16 0.3 pF, 0402) | 0 dBm | −10 dBm | ~6 mA |
| same | +8 dBm | −2.8 dBm | ~18 mA |
| **Bypassed** (15 pF in series at L2, L3/L4 bridged, C14–C16 off) | 0 dBm | **−0.01 dBm** | **~5 mA** |
| same | +8 dBm | **+7.5 dBm** | **~13 mA** |

Datasheet (nRF54L, 3.0 V, DC/DC): 5.0 mA at 0 dBm and 10.0 mA at +8 dBm.

What was learned:

1. **The PA itself is fine.** Into 50 Ω it gives the datasheet power and current.
2. **The fitted network presented a strong mismatch.** It cost a constant 10–11 dB and made the PA draw more
   current, about 18 instead of 13 mA at +8 dBm, which is what a PA into the wrong load does.
3. **The grounding follows Nordic's notes.** C14's ground goes only to pin 32 (VSS_PA), which only joins the centre
   pad, and C15 grounds straight to the bottom plane with no inner-layer fill. Nordic's network uses 0201 parts
   packed tightly. Ours was adapted to 0402 parts in a straight chain about 8.5 mm long from pin 31 to C16. The parasitics of that
   layout, or a wrong part, are the likely cause. Not resolved. The network's parts are off this board now.
4. **Supply current limit.** At +8 dBm with the network fitted the board averaged about 18 mA, and the 20 mA limit
   from BRINGUP browned it out: the carrier flickered on and off. 40 mA fixed it.
5. **The DC/DC is on:** `REGULATORS.VREGMAIN.DCDCEN` read 1 over the J-Link while the carrier ran, and the 0 dBm
   current matches the datasheet's DC/DC figure.

## Harmonics (spectrum analyser, 2026-10-28)

Board #2 with the PA network bypassed (no filtering at all). The network lost 10–11 dB of output power (see
[Output power](#output-power)), so it could not be used for a meaningful harmonics measurement. Measured with `cwtest` at 2440 MHz and the 0 dBm setting, on the
uni's R&S Spectrum Rider FPH. Same setup and settings as the C23 boards, described in
[`hardware/C23/testing/RF/RF_CARRIER.md`](../../../C23/testing/RF/RF_CARRIER.md#harmonics-spectrum-analyser-2026-10-28):
each harmonic on its own 3 MHz span, RBW 30 kHz, Auto Peak, 30 dB attenuation, levels as read with no cable
correction (about 0.5 dB at 2.4 GHz to 1–2 dB at 12 GHz).

| | Frequency | Level | Limit | Margin | File |
|---|---|---|---|---|---|
| H1 | 2440 MHz | −0.7 dBm | | | [`harm_01_bypassed_0dBm_H1_2440MHz.csv`](harm_01_bypassed_0dBm_H1_2440MHz.csv) |
| H2 | 4880 MHz | −43.2 dBm | −41.2 (FCC restricted) | +2.0 dB | [`harm_02_bypassed_0dBm_H2_4880MHz.csv`](harm_02_bypassed_0dBm_H2_4880MHz.csv) |
| **H3** | 7320 MHz | **−24.3 dBm** | −41.2 (FCC) / −30 (ETSI) | **−17.1 / −5.7 dB** ✗ | [`harm_03_bypassed_0dBm_H3_7320MHz.csv`](harm_03_bypassed_0dBm_H3_7320MHz.csv) |
| H4 | 9760 MHz | −45.9 dBm | −30 (ETSI) | +15.9 dB | [`harm_04_bypassed_0dBm_H4_9760MHz.csv`](harm_04_bypassed_0dBm_H4_9760MHz.csv) |
| H5 | 12200 MHz | −48.4 dBm | −41.2 (FCC restricted) | +7.2 dB | [`harm_05_bypassed_0dBm_H5_12200MHz.csv`](harm_05_bypassed_0dBm_H5_12200MHz.csv) |

What was learned:

1. **Rev B needs a harmonic filter on the N54.** H3 fails the FCC restricted-band limit by 17 dB and ETSI by
   6 dB already at 0 dBm. The filter needs at least about 20 dB of H3 rejection at 0 dBm, more at +8 dBm.
2. **The fair comparison between the variants is with no filter on either board.** At 0 dBm both fail the FCC
   restricted-band limit on H3, but the C23 by 0.6 dB (−40.6 dBm) and the N54 by 17 dB (−24.3 dBm). The C23's pi
   network removes 27 dB of H3 and works on its layout. The N54's reference network does not work on this
   layout yet (see [Output power](#output-power)).
3. +8 dBm was not measured: failing at 0 dBm already decides it.
4. The carrier read −0.7 dBm against 0.0 dBm on the cable-corrected VNA, which gives the FPH setup's loss at
   2.4 GHz.

## Open items

- [x] **2026-10-28 (uni, spectrum analyser):** harmonics (2nd–5th) of the bypassed board, with no filtering at all.
      H3 fails by 17 dB (FCC) at 0 dBm, so rev B needs a harmonic filter. See
      [Harmonics](#harmonics-spectrum-analyser-2026-10-28).
- [ ] Check the 11.75 pF trim on board #1.
- [ ] If rev B uses the N54: copy Nordic's 0201 PA network layout exactly, and verify it into 50 Ω before fitting
      the antenna match.

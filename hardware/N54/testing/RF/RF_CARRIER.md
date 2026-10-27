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
taken as the centre of the peak's −6 dB width. The levels below are as read; the offsets come from the same method.

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
   packed tightly; ours are 0402 in a straight chain about 8.5 mm long from pin 31 to C16. The parasitics of that
   layout, or a wrong part, are the likely cause. Not resolved; the network's parts are off this board now.
4. **Supply current limit.** At +8 dBm with the network fitted the board averaged about 18 mA, and the 20 mA limit
   from BRINGUP browned it out: the carrier flickered on and off. 40 mA fixed it.
5. **The DC/DC is on:** `REGULATORS.VREGMAIN.DCDCEN` read 1 over the J-Link while the carrier ran, and the 0 dBm
   current matches the datasheet's DC/DC figure.

## Open items

- [ ] **2026-10-28 (uni, spectrum analyser):** harmonics (2nd–5th) of the bypassed board, with no filtering at all.
      Targets: −41.2 dBm for the harmonics in FCC restricted bands (2nd, 3rd, 5th), −30 dBm (ETSI). This decides
      whether rev B needs a harmonic filter.
- [ ] Check the 11.75 pF trim on board #1.
- [ ] If rev B uses the N54: copy Nordic's 0201 PA network layout exactly, and verify it into 50 Ω before fitting
      the antenna match.

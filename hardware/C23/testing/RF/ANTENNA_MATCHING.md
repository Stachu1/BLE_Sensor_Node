# BSN-C23-A antenna matching (2026-10-23, 2026-10-26)

Matching the AE1 chip antenna (Abracon AANI-CH-0138-Q-T) to 50 Ω on a Rev A board, measured with a
Keysight P9370B VNA through J1 (U.FL).

**Result (battery connector fitted, 2026-10-26):** with **L2 = 4.3 nH (series)** and **2.1 pF on the
L3 pads (shunt)**, S11 is −32.1 dB at 2.44 GHz and better than −10.3 dB across 2.40–2.48 GHz
(file 12). These are the values to use.

Without the battery connector (2026-10-23), L2 = 3.3 nH and 2.0 pF gave −18.8 dB at 2.44 GHz and
better than −11 dB in band (file 07). Fitting the connector raises the board and detunes the antenna to
about 9 + j9 Ω (−3 dB) with those values, so they don't apply to the assembled node.

![S11 of the matching steps](s11_matching_steps.png)

The plot shows the 2026-10-23 sweeps (03–07) only.

## Test board and network

The board is an RF-only test board: no MCU, no C8 and no L1. Only J1, the matching network and AE1
are fitted, so J1 sees just the antenna path.

Topology (schematic reference designators):

```
J1 (U.FL) ── 15 pF series (DC block, C9/C6) ── node ── L2 series ── AE1 feed
                                                │
                                         L3 pads (shunt to GND)
```

- One 15 pF series cap was kept as a DC block, and the other series position was bridged. At 2.44 GHz a 0402
  15 pF cap is close to its self-resonance, and swapping it for a short made no measurable difference
  (3.1 + j18.2 vs 3.1 + j18.1 Ω).
- The shunt position used is the L3 pads (between the DC block and L2). The L4 pads (shunt at the
  antenna side) stayed empty. Shunt-first at the antenna can't reach 50 Ω here because the antenna's
  parallel resistance is below 50 Ω.
- Starting point was the TI reference values (C6 15 pF, L2 6.7 nH, L3 7.3 nH shunt), which were not
  tuned for this layout.

## Measurement setup

- Keysight P9370B, 1 port, 1.0–3.5 GHz, 201 points.
- 1-port calibration at the end of the cable, then the reference plane moved to the board with port
  extension (open, including loss).
- Checks of the reference plane (files 01 and 02):
  - Short: 1.5 + j0.0 Ω at 2.44 GHz, so the reference plane is at the board. About 1.5 Ω of residual
    loss/error remains.
  - Open: |Γ| ≈ 1.06 at 2.44 GHz (slightly above 1, so the loss compensation is a bit too high). Good
    enough to tune with, but resistances of a few ohms near the chart edge aren't accurate.
- Moving or holding the cable barely changed the readings, so cable-shield currents are not a
  significant error on this setup.
- 2026-10-26 sweeps (files 08–12): same VNA and J1 connection, 1.5–3.5 GHz, 201 points (10 MHz steps),
  with the battery connector fitted. The connector raises the board slightly. With the connector in
  place, having the coin cell in or out made almost no difference.

### First attempt: uncorrected cable (data not kept)

The first readings were single points taken with the reference plane at the VNA, not at the board:

| Network | Z at 2.44 GHz |
|---|---|
| 2 × 15 pF + 6.7 nH, L3 removed | 3.1 + j18.2 Ω |
| same + 3.9 pF on L3 pads | 50 − j265 Ω |
| 15 pF caps shorted, 6.7 nH, no shunt | 3.1 + j18.1 Ω |
| same + 5.1 pF on L3 pads | 18.4 − j126 Ω |

Values calculated from these readings never landed where predicted. A 1.0–3.5 GHz sweep then showed
series and parallel resonances repeating every ~0.25 GHz, which is the signature of an extra line, not
of an antenna. The S11 phase slope gave a round-trip delay of about 2.1 ns, i.e. about 22 cm of
uncorrected coax. All the readings above are rotated by that cable and can't be used. After moving
the reference plane to the board (previous section), the measurements below are consistent.

## Measurements

All files are the VNA's CSV export (frequency, R, X in ohms). Z at 2.40 / 2.44 / 2.48 GHz, with S11
in brackets:

| File | Network | 2.40 GHz | 2.44 GHz | 2.48 GHz | Worst in band | Best match |
|---|---|---|---|---|---|---|
| [`s11_01_check_short.csv`](s11_01_check_short.csv) | Short at the board (check) | 1.3 − j0.7 | 1.5 + j0.0 | 1.7 + j0.7 | — | — |
| [`s11_02_check_open.csv`](s11_02_check_open.csv) | Open (check) | \|Γ\| 1.05 | \|Γ\| 1.06 | \|Γ\| 1.07 | — | — |
| [`s11_03_antenna_unmatched.csv`](s11_03_antenna_unmatched.csv) | 15 pF, L2 solder-bridged, no shunt | 5.9 − j14.7 (−1.9 dB) | 6.4 − j13.0 (−2.1 dB) | 7.3 − j11.3 (−2.4 dB) | −1.9 dB | −13.3 dB @ 2.99 GHz |
| [`s11_04_L2-2n2.csv`](s11_04_L2-2n2.csv) | 15 pF, L2 2.2 nH | 13.8 + j6.0 (−4.8 dB) | 16.5 + j11.1 (−5.6 dB) | 20.2 + j16.5 (−6.5 dB) | −4.8 dB | −8.4 dB @ 2.64 GHz |
| [`s11_05_L2-2n9.csv`](s11_05_L2-2n9.csv) | 15 pF, L2 2.9 nH | 16.0 + j11.1 (−5.4 dB) | 19.5 + j17.3 (−6.2 dB) | 24.7 + j23.9 (−7.1 dB) | −5.4 dB | — |
| [`s11_06_L2-2n9_L3-1p8.csv`](s11_06_L2-2n9_L3-1p8.csv) | 15 pF, L2 2.9 nH, L3 1.8 pF | 13.9 + j10.2 (−4.7 dB) | 19.3 + j13.7 (−6.4 dB) | 26.9 + j14.9 (−9.1 dB) | −4.7 dB | −22.3 dB @ 2.56 GHz |
| [`s11_07_L2-3n3_L3-2p0.csv`](s11_07_L2-3n3_L3-2p0.csv) | **15 pF, L2 3.3 nH, L3 2.0 pF** | 30.1 + j11.2 (−11.0 dB) | **41.3 + j5.8 (−18.8 dB)** | 45.2 − j7.5 (−20.6 dB) | **−11.0 dB** | **−23.8 dB @ 2.46 GHz** |
| (no file, single reading) | same as 07, **battery fitted** | — | **9.5 + j12.3 (−3.1 dB)** | — | — | — |
| [`s11_08_bat-con_L2-3n3_L3-2p0.csv`](s11_08_bat-con_L2-3n3_L3-2p0.csv) | same as 07, battery connector fitted | 5.8 + j5.3 (−2.0 dB) | 9.0 + j9.4 (−3.0 dB) | 14.0 + j13.9 (−4.6 dB) | −2.0 dB | −29.6 dB @ 2.60 GHz |
| [`s11_09_bat-con_L2-3n9_L3-3p6.csv`](s11_09_bat-con_L2-3n9_L3-3p6.csv) | battery connector, L2 3.9 nH, L3 3.6 pF | 11.1 + j7.6 (−3.8 dB) | 13.4 + j2.6 (−4.8 dB) | 9.6 + j0.2 (−3.4 dB) | −3.4 dB | −4.8 dB @ 2.43 GHz |
| [`s11_10_bat-con_L2-3n4_L3-2p1.csv`](s11_10_bat-con_L2-3n4_L3-2p1.csv) | battery connector, L2 3.4 nH, L3 2.1 pF | 6.8 + j9.4 (−2.3 dB) | 10.7 + j14.4 (−3.5 dB) | 18.4 + j19.7 (−5.6 dB) | −2.3 dB | −35.0 dB @ 2.57 GHz |
| [`s11_11_bat-con_L2-3n9_L3-2p1.csv`](s11_11_bat-con_L2-3n9_L3-2p1.csv) | battery connector, L2 3.9 nH, L3 2.1 pF | 18.3 + j17.4 (−5.8 dB) | 35.0 + j18.5 (−11.2 dB) | 51.1 + j0.8 (−37.2 dB) | −5.8 dB | −37.2 dB @ 2.48 GHz |
| [`s11_12_bat-con_L2-4n3_L3-2p1.csv`](s11_12_bat-con_L2-4n3_L3-2p1.csv) | **battery connector, L2 4.3 nH, L3 2.1 pF** | 32.5 + j18.8 (−10.3 dB) | **51.5 + j2.0 (−32.1 dB)** | 44.7 − j22.3 (−12.6 dB) | **−10.3 dB** | **−32.1 dB @ 2.44 GHz** |

Impedances in ohms. "In band" is 2.40–2.48 GHz.

## What was learned

1. **Unmatched antenna (03):** on this board AE1 has its series resonance at 2.69 GHz. At 2.44 GHz it
   is about 6.4 − j13 Ω: low resistance and slightly capacitive. The TI reference value of 6.7 nH for
   L2 is about three times too much inductance for this layout.
2. **Solder bridge vs. real part (03 → 04):** going from a solder blob to a 2.2 nH inductor at L2 also
   changed the *resistance* curve (6.4 → 16.5 Ω at 2.44 GHz, and the antenna's resonances moved about
   300 MHz lower). A series inductor can only add reactance, so the large blob itself changed how the
   antenna is fed. **Use a 0 Ω 0402 resistor instead of a solder blob for "bridged" measurements.**
3. **Calculated values only approximately hold:** each step was predicted from the previous sweep,
   but the parts, pads and rework shift the result by about one standard value. Tuning worked by
   changing one or two parts at a time, sweeping, and reading where the match had moved.
4. **Shifting the matched frequency (06 → 07):** with 2.9 nH + 1.8 pF the network was already matched
   (−22 dB), but at 2.56 GHz. Scaling both parts by (2.56 / 2.44)² ≈ 1.1 (→ 3.3 nH + 2.0 pF) moved the
   match to 2.46 GHz as predicted.
5. **Battery (07 vs. battery reading):** with the network values removed, the antenna alone goes from about
   13.8 − j31 Ω without the battery to about 4.8 − j41 Ω with it. Its resistance roughly drops to a
   third. That costs efficiency that matching can't recover. File 08 (battery connector, 3.3 nH +
   2.0 pF) reproduces the 23 Oct battery reading, and on 26 Oct the cell in or out made almost no
   difference. So the detuning comes from the connector and the raised board, not the cell itself.
6. **The series inductor sets the match, the shunt cap only finishes it (10 → 12):** a shunt part adds
   susceptance only, so L2 alone has to bring the real part of the admittance to 1/50 Ω = 20 mS at
   2.44 GHz. With 3.4 nH (10) it was about 41 mS, so the 2.1 pF cap (+32 mS) hardly moved the 2.44 GHz
   point and the match ended up at 2.57 GHz instead. With 4.3 nH (12) the real part is about 19 mS and
   the same cap cancels the remaining −33 mS, taking the antenna branch from about 13 + j23 Ω (−4 dB) to 51.5 + j2 Ω
   (−32 dB). Tune L2 first (on the 20 mS circle of the admittance chart), then pick the cap.
7. **The model drifted as L2 grew:** the antenna impedance backed out of each sweep (with ideal parts)
   has a resistance at 2.44 GHz of about 5 Ω for files 08 and 10, 9 Ω for 11 and 13 Ω for 12. A model based on
   file 08 therefore asked for too little inductance and too much capacitance (3.8 nH + 3.7 pF instead of
   4.3 nH + 2.1 pF). Some of the extra resistance may be loss in the part, pads or joint rather than
   radiation, which S11 can't distinguish. The RSSI check below settles it.
8. **File 09 doesn't fit the other sweeps:** 3.9 nH + 3.6 pF measured −4.8 dB where the model expected
   about −16 dB. No change of part value or placement reproduces it, so it was most likely a bad joint
   or a mislabelled part. It wasn't repeated.
9. **Bandwidth is set by the antenna:** at about 5–13 Ω the antenna Q is high, and a 2-element match
   reaches only about −10 dB at the band edges. Adding a third part on the existing pads (input series
   position, or the L4 pads) gained at most about 1 dB in simulation. More bandwidth needs a higher antenna
   resistance, i.e. the battery/connector further from AE1.

## Open items

- [x] **Re-match with the battery connector fitted** (2026-10-26): L2 = 4.3 nH, 2.1 pF on the L3 pads,
      −32.1 dB at 2.44 GHz and better than −10.3 dB in band (file 12).
- [ ] Check the final match in the enclosure, if there is one.
- [ ] Confirm on a working board with the radio: compare RSSI with `tools/bsn_scan.py` at a fixed
      distance and orientation for the TI reference values, the new values, and one step either side.
- [ ] Rev B: move the battery further from AE1, or at least outside the antenna keep-out area in the
      AANI-CH-0138 datasheet.
- [x] Update the RF network table in [`../../README.md`](../../README.md) with the battery-connector values.

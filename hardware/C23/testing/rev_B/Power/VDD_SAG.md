# BSN-C23-B VDD sag during an advert, against bulk capacitance (0, 1 and 2 × 100 µF)

Scope captures of VDD on a CR2032 during one advertising event, on the three boards built with different bulk
capacitance on VDD (T3 part 1, and the bulk capacitance comparison planned at the rev B build on 2026-11-13).

- Raw data: [`vdd_sag_2026-11-20/`](vdd_sag_2026-11-20/) (`scope_0.csv` to `scope_16.csv`, two screenshots).
  Original scope file names kept. The scope clock reads 21 Nov 00:20–00:43, the session was the evening of
  2026-11-20.
- Script: [`vdd_sag.py`](vdd_sag.py) recomputes the scope measurements (the CSV holds only the trace) and makes
  the plots and [`vdd_sag_summary.csv`](vdd_sag_summary.csv).

## Setup

- Keysight MSO-X 4154G, one channel on VDD. Captures 0–9 at 4 µs per sample with a 12.6 µV step (likely High-Res
  mode), 10–16 at 1.25 µs with an 83.7 µV step. Noise before the event is about 0.45 mV σ in all 17.
- Bulk capacitance is C6, Murata GRM21BR60J107ME15 (100 µF, 6.3 V, X5R, 0805). Its value at about 3 V DC bias was
  not looked up.
- Firmware, TX power and advert interval: not recorded here. **Open:** fill in.

| Board | Bulk capacitance on VDD |
|---|---|
| B #1 | none |
| B #2 | 1 × 100 µF |
| B #3 | 2 × 100 µF |

Cells are numbered after the board they came with (cell 1 from B #1 and so on).

| Captures | Board | Cell | Note |
|---|---|---|---|
| 0–4 | B #2, 1 × 100 µF | cell 2 | |
| 5–9 | B #1, no bulk capacitor | cell 1 | |
| 10–14 | B #3, 2 × 100 µF | cell 3 | |
| 15 | B #2, 1 × 100 µF | cell 3, moved from B #3 | one capture |
| 16 | B #1, no bulk capacitor | cell 3, after B #2 | one capture |
| `scope_17.png` | B #1, no bulk capacitor | cell 3 | screenshot, Pk-Pk 45.8 mV, Top 3.0379 V, Min 2.9921 V |
| `scope_18.png` | B #1, no bulk capacitor | cell 3 | infinite persistence, Pk-Pk 45.8 mV, Top 3.0466 V, Min 3.0008 V |

The board of sets 0–4 and 10–14 is from the user's memory of the order (B #2, B #1, B #3). The data agree with it:
the RC fit below gives the same capacitance for 0–4 and for 15 (both B #2) and about 1.6 times that for 10–14. The
B #1 sets have sharp edges and fit with τ ≈ 0.

## Data check

- 17 CSVs, 5000 or 16000 points each, no gaps, no NaN, no sample at a rail (no clipping).
- Repeats agree: dip σ 0.3–0.4 mV within each 5-capture set, drop area σ about 1 %.
- The persistence screenshot shows the same shape over many events on B #1, trace width a few mV.
- Event timing varies between adverts. In captures 6, 9 and 11 the TX burst comes about 0.5–1.5 ms later after
  the first step than in the others. Cause not investigated. It does not change the dip depth.
- **Cell 3 changed state at the swaps.** V_base was 3.306 V on B #3 (10–14, 00:27), 3.077 V on B #2 (15, 00:32),
  3.028 V on B #1 (16, 00:38), then rising again, 3.038 V (Top, 00:40) and 3.047 V (00:43) in the screenshots.
  The fitted source resistance, relative to cell 1, was 0.64 on B #3, 0.35 on B #2 and 0.41 on B #1. The scale
  applies to the whole event, including the steps before TX where bulk capacitance makes no difference, so it is
  the source and not the TX current. **Cause (the user, 2026-11-20):** the cell is shorted every time it is taken
  out of the holder, to get it out without tearing the holder off the board. So 15 and 16 are on a cell that had
  just been hard shorted, and the 230 mV fall followed by a slow rise is the cell recovering from that.
- So the three captures on cell 3 (14, 15, 16) are the same cell but not the same cell state. The raw dips cannot
  be compared directly. B #3 has the largest dip (55.9 mV) because the cell had about 1.5 times the resistance
  it had at 16.

## Results

Means of 5 captures (± σ), single captures for 15 and 16. dV is the dip below the pre-event level on a 50 µs
moving average. V_pp, V_top and V_min use the raw samples like the scope.

| Board, cell (captures) | V_base | V_top | V_min | V_pp | dV | Drop area | τ (RC fit) |
|---|---|---|---|---|---|---|---|
| B #2, 1 × 100 µF, cell 2 (0–4) | 3.0065 V | 3.0065 V | 2.9171 V | 90.8 ± 0.3 mV | 88.8 ± 0.4 mV | 392 mV·ms | 500 µs |
| B #1, no bulk C, cell 1 (5–9) | 2.9672 V | 2.9671 V | 2.8678 V | 100.9 ± 0.3 mV | 98.6 ± 0.3 mV | 381 mV·ms | – |
| B #3, 2 × 100 µF, cell 3 (10–14) | 3.3060 V | 3.3042 V | 3.2497 V | 57.8 ± 0.3 mV | 55.7 ± 0.3 mV | 245 mV·ms | 515 µs |
| B #2, 1 × 100 µF, cell 3 (15) | 3.0767 V | 3.0766 V | 3.0424 V | 35.5 mV | 33.6 mV | 143 mV·ms | 187 µs |
| B #1, no bulk C, cell 3 (16) | 3.0278 V | 3.0278 V | 2.9846 V | 44.6 mV | 42.0 mV | 166 mV·ms | – |

### RC model

With the cell as a source resistance R and the bulk capacitance C on VDD, the drop with C is the drop without C
through a first-order low-pass with τ = RC, scaled by k = R / R_template. Fitted for τ, k and a time shift, with a
B #1 capture as the template ([`vdd_sag_rc_fit.png`](vdd_sag_rc_fit.png)):

- The fit residual is 0.6–0.9 mV rms on every capture with bulk C, about the trace noise. The model describes
  the data.
- Null test: a B #1 capture fitted against another B #1 capture gives τ 16 µs and k 0.99.
- The drop area scales with k, as it should when the capacitors only move charge in time: 392/381 = 1.03
  against k 1.02, 245/381 = 0.64 against k 0.64, 143/166 = 0.86 against k 0.85.
- C as τ / R with R relative to cell 1: B #2 492 (0–4) and 535 (15), B #3 809 (10–14). The two B #2 values agree
  within 9 %. B #3 / B #2 = 1.58, not 2. The absolute C needs the source resistance in ohms, which needs the
  current. Not measured here.

### Effect of the bulk capacitance on one cell (model, [`vdd_sag_model_caps.png`](vdd_sag_model_caps.png))

Each cell's B #1 trace, low-passed with the fitted C:

| Cell | No bulk C | 1 × 100 µF | 2 × 100 µF |
|---|---|---|---|
| cell 1 (R 1.00) | 98.9 mV (measured) | 86.1 mV (−13 %), τ 513 µs | 79.3 mV (−20 %), τ 809 µs |
| cell 3 at 16 (R 0.41) | 42.0 mV (measured) | 38.8 mV (−8 %), τ 212 µs | 37.4 mV (−11 %), τ 334 µs |

Measured on cell 3: 42.0 mV on B #1 (16) and 33.6 mV on B #2 (15), −20 %. About half of that comes from the
cell's lower resistance at 15 (38.8 × 0.85 = 32.9 mV, against 33.6 mV measured).

- **The bulk capacitors cut the peak of the dip only partly.** The TX part is three channel bursts of about
  0.4 ms each over about 2 ms, and τ is 0.2–0.8 ms. The capacitors smooth the short steps and the gaps between
  channels, but the dip still reaches most of the depth without them.
- **The higher the cell resistance, the more the capacitors help** (τ = RC and the relative cut grows with τ). A
  cell near end of life has a higher resistance, so the cut there will be larger than on these cells. Not
  measured.
- **Recovery:** the capacitors delay the return by about τ (0.2–0.8 ms) after each step. Time from onset until
  the drop stays below 10 mV: 9.1 ms (B #1, cell 1), 9.7 ms (B #2, cell 2), 8.6 ms (B #3, cell 3), 7.5 and
  7.3 ms on cell 3 (B #1 and B #2). The tail after the event (a few mV, several ms) is the cell's own slow
  recovery and is the same with and without bulk capacitance.

## Open

- Firmware build, TX power and interval for these captures.
- **Redo planned (decided 2026-11-20):** 3.0 V bench supply with about 30 Ω in series in place of the cell, the
  same source on all three boards, 5 captures each. Gives measured numbers in place of the model ones, the event
  current from I = ΔV / R and the absolute C from τ = RC. This CR2032 run stays as the real-cell reference.
- T3 itself: a partly used cell, and the current during the event for R in ohms and C at bias.

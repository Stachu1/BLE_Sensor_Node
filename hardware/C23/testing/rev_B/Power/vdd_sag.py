"""VDD sag on the CR2032 during one advertising event, BSN-C23-B, 0 / 1 / 2 x 100 uF, scope 2026-11-20.

Raw data: vdd_sag_2026-11-20/scope_N.csv (Keysight MSO-X 4154G, one channel on VDD, time [s], volt [V]).
The scope measurements (Pk-Pk, Top, Min) are not in the CSV, so they are recomputed here.

Run: python vdd_sag.py [out dir]   (default: this folder). Needs numpy, scipy, matplotlib.

Writes:
  vdd_sag_summary.csv        one row per capture, all metrics
  vdd_sag_same_cell.png      cell 3 on B #3 (14), B #2 (15) and B #1 (16)
  vdd_sag_repeats.png        the three 5-capture sets, repeats overlaid
  vdd_sag_rc_fit.png         traces with bulk capacitance against the low-passed trace without (RC model)
  vdd_sag_metrics.png        dip depth, RC tau and drop area per capture
  vdd_sag_model_caps.png     model: 0, 1 and 2 x 100 uF on the same cell (cell 1 and cell 3)

Metric definitions (all on the VDD node at the scope probe):
  V_base   mean of the first 1.5 ms (before the event)
  V_top    most common value in the upper half of the trace, 0.25 mV bins (like the scope's Top)
  V_min    lowest raw sample (like the scope's Min, includes noise)
  V_pp     V_max - V_min, raw samples (like the scope's Pk-Pk)
  dV       V_base minus the minimum of the 50 us moving average (dip depth without noise)
  onset    first time the smoothed drop exceeds 3 mV
  t_min    time of the smoothed minimum after onset
  t_rec50  from t_min until the drop is below 50 % of dV and stays there
  t_rec90  from t_min until the drop is below 10 % of dV and stays there (long when the cell's own
           slow recovery tail is larger than 10 % of dV)
  t_settle10  from onset until the drop is below 10 mV and stays there
  area     integral of the drop over the window, mV*ms (charge times source resistance, so the caps
           should move it around in time but not change it for the same cell and same current)
RC model: with a source resistance R and a bulk capacitance C at VDD, the drop with C is the drop without C
passed through a first-order low-pass with tau = R*C, times k = R_capped / R_template. Fitted for tau, k and a
time shift.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import least_squares
from scipy.signal import lfilter

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "vdd_sag_2026-11-20")
OUT = sys.argv[1] if len(sys.argv) > 1 else HERE

# Capture sets. caps = number of 100 uF bulk capacitors (C6) on VDD. Boards from hardware/C23/README.md:
# B #1 none, B #2 one, B #3 two. The board of sets 0-4 and 10-14 is from the user's memory (order B #2, B #1,
# B #3), the sets without bulk capacitor are confirmed by the waveform (sharp edges, RC fit tau ~ 0).
# Cells are numbered after the board they came with. Each board ran its own cell for the first 15 captures,
# then cell 3 (from B #3) was moved to B #2 (15) and B #1 (16).
SETS = [
    dict(name="B #2, 1 x 100 µF, cell 2", caps=1, cell="cell 2", idx=[0, 1, 2, 3, 4]),
    dict(name="B #1, no bulk C, cell 1",  caps=0, cell="cell 1", idx=[5, 6, 7, 8, 9]),
    dict(name="B #3, 2 x 100 µF, cell 3", caps=2, cell="cell 3", idx=[10, 11, 12, 13, 14]),
    dict(name="B #2, 1 x 100 µF, cell 3", caps=1, cell="cell 3", idx=[15]),
    dict(name="B #1, no bulk C, cell 3",  caps=0, cell="cell 3", idx=[16]),
]
CAPCOL = {0: "#2a78d6", 1: "#eb6834", 2: "#1baf7a"}  # categorical slots 1-3
BOARD = {0: "B #1", 1: "B #2", 2: "B #3"}
BULK = {0: "no bulk capacitor", 1: "1 x 100 µF", 2: "2 x 100 µF"}
# RC fits: (capture with bulk C, template without). Same cell where possible (15 vs 16). For the own-cell sets the
# template is set 5-9 on B #1 (another cell), k then carries the resistance ratio of the two cells.
FITS = [(0, 5), (1, 6), (2, 7), (3, 8), (4, 9), (10, 5), (11, 6), (12, 7), (13, 8), (14, 9),
        (15, 16), (6, 5), (16, 5)]

SMOOTH_S = 50e-6
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.3,
                     "axes.spines.top": False, "axes.spines.right": False})


def load(i):
    d = np.loadtxt(os.path.join(RAW, f"scope_{i}.csv"), delimiter=",", skiprows=2)
    return d[:, 0], d[:, 1]


def smooth(v, dt, w=SMOOTH_S):
    n = max(1, int(round(w / dt)))
    k = np.ones(n) / n
    return np.convolve(np.r_[np.full(n, v[0]), v, np.full(n, v[-1])], k, "same")[n:-n]


def metrics(i):
    t, v = load(i)
    dt = np.median(np.diff(t))
    base = v[t < t[0] + 1.5e-3].mean()
    vs = smooth(v, dt)
    drop = base - vs
    i_on = int(np.argmax(drop > 3e-3))
    i_min = i_on + int(np.argmax(drop[i_on:]))
    dv = drop[i_min]
    after = drop[i_min:]

    def settle(frac):
        above = np.nonzero(after > frac * dv)[0]
        j = above[-1] + 1 if len(above) else 0
        return np.nan if i_min + j >= len(t) - 1 else t[i_min + j] - t[i_min]

    above10 = np.nonzero(drop > 10e-3)[0]
    t_set10 = np.nan if not len(above10) or above10[-1] >= len(t) - 2 else t[above10[-1] + 1] - t[i_on]
    mid = 0.5 * (v.max() + v.min())
    up = v[v > mid]
    h, e = np.histogram(up, bins=np.arange(up.min(), up.max() + 2.5e-4, 2.5e-4))
    top = 0.5 * (e[np.argmax(h)] + e[np.argmax(h) + 1])
    return dict(scope=i, dt_us=dt * 1e6, n=len(v), V_base=base, V_top=top, V_max=v.max(), V_min=v.min(),
                V_pp_mV=(v.max() - v.min()) * 1e3, dV_mV=dv * 1e3, noise_mV=v[t < t[0] + 1.5e-3].std() * 1e3,
                onset_ms=t[i_on] * 1e3, t_min_ms=t[i_min] * 1e3, t_min_from_onset_ms=(t[i_min] - t[i_on]) * 1e3,
                t_rec50_ms=settle(0.5) * 1e3, t_rec90_ms=settle(0.1) * 1e3,
                t_settle10_ms=t_set10 * 1e3,
                area_mVms=np.trapezoid(base - v, t) * 1e6)


def drop_aligned(i):
    t, v = load(i)
    dt = np.median(np.diff(t))
    base = v[t < t[0] + 1.5e-3].mean()
    d = base - v
    t_on = t[int(np.argmax(base - smooth(v, dt) > 3e-3))]
    return t - t_on, d


def lpf(x, tau, dt):
    a = dt / (tau + dt)
    return lfilter([a], [1, -(1 - a)], x, zi=[x[0] * (1 - a)])[0]


def rc_fit(ic, i0):
    tc, dc = drop_aligned(ic)
    t0, d0 = drop_aligned(i0)
    dt = np.median(np.diff(tc))

    def model(p):
        k, lt, s = p
        return k * lpf(np.interp(tc - s, t0, d0, left=0, right=d0[-1]), np.exp(lt), dt)

    best = None
    for lt0 in np.log([20e-6, 100e-6, 300e-6, 1e-3]):
        r = least_squares(lambda p: model(p) - dc, [1, lt0, 0],
                          bounds=([0.1, np.log(1e-6), -2e-3], [5, np.log(5e-3), 2e-3]), x_scale=[0.1, 0.3, 1e-4])
        if best is None or r.cost < best.cost:
            best = r
    k, lt, s = best.x
    return dict(capped=ic, template=i0, k=k, tau_us=np.exp(lt) * 1e6, shift_us=s * 1e6,
                rms_mV=np.sqrt(np.mean(best.fun ** 2)) * 1e3, t=tc, meas=dc, model=model(best.x))


def set_of(i):
    return next(s for s in SETS if i in s["idx"])


# ---------------------------------------------------------------- metrics table
rows = []
for s in SETS:
    for i in s["idx"]:
        m = metrics(i)
        m.update(set=s["name"], caps=s["caps"], cell=s["cell"], board=BOARD[s["caps"]])
        rows.append(m)
fits = [rc_fit(a, b) for a, b in FITS]
fit_by = {f["capped"]: f for f in fits if set_of(f["capped"])["caps"] > 0}  # fits on B #1 are null tests

cols = ["scope", "set", "caps", "board", "cell", "dt_us", "n", "noise_mV", "V_base", "V_top", "V_max", "V_min",
        "V_pp_mV", "dV_mV", "onset_ms", "t_min_ms", "t_min_from_onset_ms", "t_rec50_ms", "t_rec90_ms",
        "t_settle10_ms", "area_mVms", "rc_template", "rc_k", "rc_tau_us", "rc_rms_mV"]
with open(os.path.join(OUT, "vdd_sag_summary.csv"), "w", encoding="utf-8") as f:
    f.write(",".join(cols) + "\n")
    for m in rows:
        ft = fit_by.get(m["scope"])
        m.update(rc_template=ft["template"] if ft else "", rc_k=ft["k"] if ft else "",
                 rc_tau_us=ft["tau_us"] if ft else "", rc_rms_mV=ft["rms_mV"] if ft else "")
        f.write(",".join(f"{m[c]:.6g}" if isinstance(m[c], (float, np.floating)) else str(m[c]) for c in cols)
                + "\n")

print(f"{'#':>3} {'set':18} {'V_base':>7} {'V_top':>7} {'V_min':>7} {'Vpp':>6} {'dV':>6} {'rec50':>6} "
      f"{'rec90':>6} {'set10':>6} {'area':>6}")
for m in rows:
    print(f"{m['scope']:>3} {m['set']:18} {m['V_base']:7.4f} {m['V_top']:7.4f} {m['V_min']:7.4f} "
          f"{m['V_pp_mV']:6.1f} {m['dV_mV']:6.1f} {m['t_rec50_ms']:6.2f} {m['t_rec90_ms']:6.2f} {m['t_settle10_ms']:6.2f} "
          f"{m['area_mVms']:6.1f}")
print("\nset means (n = 5 where a set has 5):")
for s in SETS:
    sel = [m for m in rows if m["scope"] in s["idx"]]
    def ms(key):
        x = np.array([m[key] for m in sel])
        return f"{x.mean():.2f}" + (f" +- {x.std(ddof=1):.2f}" if len(x) > 1 else "")
    print(f"  {s['name']:18} dV {ms('dV_mV')} mV, Vpp {ms('V_pp_mV')} mV, rec50 {ms('t_rec50_ms')} ms, "
          f"rec90 {ms('t_rec90_ms')} ms, settle10 {ms('t_settle10_ms')} ms, area {ms('area_mVms')} mV*ms")
print("\nRC fits (k = R_capped / R_template, tau = R*C):")
for f in fits:
    print(f"  {f['capped']:>2} vs {f['template']:>2}: k {f['k']:.3f}, tau {f['tau_us']:6.1f} us, "
          f"rms {f['rms_mV']:.2f} mV")

# ---------------------------------------------------------------- figure 1: same cell
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6))
for i, caps in [(16, 0), (15, 1), (14, 2)]:
    t, v = load(i)
    a1.plot(t * 1e3, v, color=CAPCOL[caps], lw=0.6, label=f"scope_{i}: {BOARD[caps]}, {BULK[caps]}")
    ta, d = drop_aligned(i)
    m = next(r for r in rows if r["scope"] == i)
    a2.plot(ta * 1e3, d * 1e3, color=CAPCOL[caps], lw=0.6,
            label=f"{BOARD[caps]}, {BULK[caps]}: dip {m['dV_mV']:.1f} mV")
a1.set(xlabel="time [ms] (scope trigger at 0)", ylabel="VDD [V]",
       title="VDD (absolute, V_base not settled between boards)")
a2.set(xlabel="time from event onset [ms]", ylabel="drop below V_base [mV]",
       title="Drop below the pre-event level, aligned at onset")
a2.invert_yaxis()
for a in (a1, a2):
    a.legend(loc="lower right" if a is a1 else "lower right", fontsize=8)
fig.suptitle("BSN-C23-B, one CR2032 (cell 3) moved from B #3 (scope_14) to B #2 (scope_15) to B #1 (scope_16), 2026-11-20")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "vdd_sag_same_cell.png"), dpi=150)

# ---------------------------------------------------------------- figure 2: repeats
fig, axs = plt.subplots(1, 3, figsize=(14, 4.4), sharey=True)
for a, s in zip(axs, SETS[:3]):
    for i in s["idx"]:
        ta, d = drop_aligned(i)
        a.plot(ta * 1e3, d * 1e3, color=CAPCOL[s["caps"]], lw=0.5, alpha=0.7)
    dv = [m["dV_mV"] for m in rows if m["scope"] in s["idx"]]
    a.set(title=f"{BOARD[s['caps']]}, {BULK[s['caps']]}, {s['cell']}, n = 5\n"
                f"dip {np.mean(dv):.1f} ± {np.std(dv, ddof=1):.1f} mV",
          xlabel="time from event onset [ms]", xlim=(-1, 14))
axs[0].set_ylabel("drop below V_base [mV]")
axs[0].invert_yaxis()
fig.suptitle("Repeatability, 5 captures per board, each board on its own cell (cells differ, so depths are not "
             "comparable between panels)")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "vdd_sag_repeats.png"), dpi=150)

# ---------------------------------------------------------------- figure 3: RC fit
show = [f for f in fits if f["capped"] in (0, 10, 15)]
fig, axs = plt.subplots(1, 3, figsize=(14, 4.4))
for a, f in zip(axs, show):
    caps = set_of(f["capped"])["caps"]
    a.plot(f["t"] * 1e3, f["meas"] * 1e3, color=CAPCOL[caps], lw=0.6, label=f"measured scope_{f['capped']}")
    a.plot(f["t"] * 1e3, f["model"] * 1e3, color="0.15", lw=1.0, ls="--",
           label=f"scope_{f['template']} (B #1, no bulk C) low-passed")
    a.set(title=f"{BOARD[caps]}, {BULK[caps]}: tau {f['tau_us']:.0f} µs, k {f['k']:.2f}, rms {f['rms_mV']:.2f} mV",
          xlabel="time from event onset [ms]", xlim=(-1, 14))
    a.invert_yaxis()
    a.legend(loc="lower right", fontsize=8)
axs[0].set_ylabel("drop below V_base [mV]")
fig.suptitle("RC model: drop with bulk C = k x first-order low-pass (tau = R C) of the drop on B #1 (no bulk C)")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "vdd_sag_rc_fit.png"), dpi=150)

# ---------------------------------------------------------------- figure 4: metrics
fig, axs = plt.subplots(1, 3, figsize=(14, 4.2))
labels = [s["name"].replace(", ", "\n") for s in SETS]
for a, key, yl in zip(axs, ["dV_mV", "rc_tau_us", "area_mVms"],
                      ["dip depth dV [mV]", "RC time constant tau [µs] (B #1: no fit)",
                       "area of the drop [mV ms]"]):
    for x, s in enumerate(SETS):
        y = [m[key] for m in rows if m["scope"] in s["idx"] and m[key] != ""]
        if not y:
            continue
        a.plot(np.full(len(y), x) + np.linspace(-0.12, 0.12, len(y)), y, "o", ms=6,
               color=CAPCOL[s["caps"]], mec="white", mew=1)
    a.set_xticks(range(len(SETS)), labels, fontsize=8)
    a.set_ylabel(yl)
    a.axvspan(1.5, 4.5, color="0.5", alpha=0.08, lw=0)
    a.set_ylim(bottom=0)
axs[0].text(3.0, axs[0].get_ylim()[1] * 0.97, "cell 3", ha="center", va="top", fontsize=8, color="0.35")
fig.suptitle("Per capture. Shaded: cell 3, on B #3 (5 captures), then B #2 and B #1 (one capture each)")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "vdd_sag_metrics.png"), dpi=150)

# ---------------------------------------------------------------- capacitance and model prediction
# k chains the source resistance to cell 1 (scope 5-9): R(cell) / R(cell 1).
k_of = {f["capped"]: f for f in fits}
r1 = np.mean([k_of[i]["k"] for i in range(0, 5)])            # cell 2
r2a = np.mean([k_of[i]["k"] for i in range(10, 15)])         # cell 3 at scope 10-14
r16 = k_of[16]["k"]                                          # cell 3 at scope 16
r15 = r16 * k_of[15]["k"]                                    # cell 3 at scope 15
c1a = np.mean([k_of[i]["tau_us"] for i in range(0, 5)]) / r1      # C in us per R(cell 1)
c1b = k_of[15]["tau_us"] / r15
c2 = np.mean([k_of[i]["tau_us"] for i in range(10, 15)]) / r2a
C1 = 0.5 * (c1a + c1b)
print(f"\nsource R relative to cell 1: cell 2 {r1:.3f}, cell 3 at 10-14 {r2a:.3f}, at 15 {r15:.3f}, at 16 {r16:.3f}")
print(f"C = tau / R_rel [us]: B #2 (0-4) {c1a:.0f}, B #2 (15) {c1b:.0f}, B #3 (10-14) {c2:.0f}, "
      f"C2/C1 = {c2 / C1:.2f}")

fig, axs = plt.subplots(1, 2, figsize=(12, 4.6))
for a, (tmpl, rr, cname, meas) in zip(axs, [(5, 1.0, "cell 1 (template scope_5 on B #1)", {0: None}),
                                            (16, r16, "cell 3 (template scope_16 on B #1)", {0: None, 1: 15})]):
    t0, d0 = drop_aligned(tmpl)
    dt = np.median(np.diff(t0))
    for n, c in [(0, 0.0), (1, C1), (2, c2)]:
        tau = rr * c * 1e-6
        d = d0 if tau == 0 else lpf(d0, tau, dt)
        lab = BULK[n] + ("" if n == 0 else f", model tau {tau * 1e6:.0f} µs") + \
              f": dip {smooth(d, dt).max() * 1e3:.1f} mV"
        if n in meas and meas[n] is not None:
            lab += f" (measured scope_{meas[n]}: {next(r['dV_mV'] for r in rows if r['scope'] == meas[n]):.1f})"
        a.plot(t0 * 1e3, d * 1e3, color=CAPCOL[n], lw=0.7 if n == 0 else 1.0, label=lab)
    a.set(title=cname, xlabel="time from event onset [ms]", xlim=(-1, 14))
    a.invert_yaxis()
    a.legend(loc="lower right", fontsize=8)
axs[0].set_ylabel("drop below V_base [mV]")
fig.suptitle(f"Model: one cell's trace without bulk C low-passed with tau = R C (C from the fits, C2/C1 = {c2 / C1:.2f}), "
             "same cell and same event")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "vdd_sag_model_caps.png"), dpi=150)
print("\nwrote figures and vdd_sag_summary.csv to", OUT)

"""Supply current and VDD sag during one advertising event, on a bench supply with a series resistor.

BSN-C23-B B #1 (no bulk C), B #2 (1 x 100 uF), B #3 (2 x 100 uF) and BSN-N52-A A #3 (47 uF), scope 2026-11-26.

Raw data: vdd_sag_2026-11-26/<board>_<what>_<supply>_<n>.csv (Keysight MSO-X 4154G, time [s], volt [V]),
the N52 files in hardware/N52/testing/Power/vdd_sag_2026-11-26/.
  what = shunt: voltage across the 22.41 ohm series resistor, so supply current I = V / R
  what = vdd:   VDD at the board, behind the same resistor
  supply = 3V0 / 2V4 / 2V0: bench supply 3.004 / 2.4036 / 2.0035 V. n = 1..5 repeats.
scope_file_map.csv in the same folder maps the original scope_N.csv names to the new ones.

Run: python vdd_sag.py [out dir]   (default: this folder). Needs numpy, scipy, matplotlib.

Writes:
  vdd_sag_summary.csv        one row per capture, all metrics
  vdd_sag_current.png        supply current per board, one panel per supply voltage
  vdd_sag_vdd.png            VDD at 2.0 V supply, and the current from the VDD drop against the shunt current
  vdd_sag_repeats.png        all 80 captures, 5 repeats overlaid per board and condition
  vdd_sag_metrics.png        peak current, charge per event and VDD dip against supply voltage
  vdd_sag_rc_fit.png         B #2 and B #3 current against the B #1 current low-passed (RC model)

Metric definitions:
  offset    mean of the first 0.2 ms of the capture (before the event). Subtracted from shunt captures,
            V_base for VDD captures
  I         (V_shunt - offset) / R, or (V_base - V_vdd) / R for VDD captures (same series R, same current)
  I_peak    maximum of I on a 50 us moving average
  E         energy into the board, V_supply * Q - R * integral(I^2) (the loss in the series R taken out,
            tail not included)
  Q         integral of I over the capture, plus the exponential tail past the capture end (I_end * tau)
  t_event   time from I first above 1 mA until I last above 1 mA
  tau       time constant of the decay after the last TX burst, exponential fit from 70 % to 10 % of the
            peak current. With the series R it gives C = tau / R (approximate, see VDD_SAG.md)
  dV        V_base minus the minimum of the 50 us moving average (VDD captures only)
RC model: the B #2 / B #3 current is the B #1 current at the same supply through a first-order low-pass with
tau = R C, times k (charge ratio). Fitted for tau, k and a time shift.
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
RAW = os.path.join(HERE, "vdd_sag_2026-11-26")
RAW_N52 = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "N52", "testing", "Power", "vdd_sag_2026-11-26"))
OUT = sys.argv[1] if len(sys.argv) > 1 else HERE

R_SER = 22.41                                   # ohm, measured 2026-11-25 (22.410)
SUPPLY = {"3V0": 3.004, "2V4": 2.4036, "2V0": 2.0035}
BOARDS = ["B1", "B2", "B3", "N52-A3"]
LABEL = {"B1": "B #1, no bulk C", "B2": "B #2, 1 x 100 µF", "B3": "B #3, 2 x 100 µF",
         "N52-A3": "N52 A #3, 47 µF"}
SHORT = {"B1": "B #1", "B2": "B #2", "B3": "B #3", "N52-A3": "N52 A #3"}
COL = {"B1": "#2a78d6", "B2": "#eb6834", "B3": "#1baf7a", "N52-A3": "#6250d6"}  # slots 1, 2, 3, 7
LS = {"B1": "-", "B2": "--", "B3": "-.", "N52-A3": ":"}
MK = {"B1": "o", "B2": "s", "B3": "^", "N52-A3": "D"}
CONDS = [("shunt", "3V0"), ("shunt", "2V4"), ("shunt", "2V0"), ("vdd", "2V0")]
N_REP = 5
SMOOTH_S = 50e-6
SHOW = 3                                        # capture shown in the single-trace figures (1 is an outlier on
                                                # B #2 shunt 2.0 V and B #1 VDD 2.0 V)

plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.3,
                     "axes.spines.top": False, "axes.spines.right": False})


def fname(b, what, sup, n):
    return f"{b}_{what}_{sup}_{n}.csv"


def load(b, what, sup, n):
    d = np.genfromtxt(os.path.join(RAW_N52 if b.startswith("N52") else RAW, fname(b, what, sup, n)), delimiter=",", skip_header=2)
    d = d[~np.isnan(d).any(axis=1)]             # the scope pads the last rows with empty values
    return d[:, 0], d[:, 1]


def smooth(v, dt, w=SMOOTH_S):
    n = max(1, int(round(w / dt)))
    k = np.ones(n) / n
    return np.convolve(np.r_[np.full(n, v[0]), v, np.full(n, v[-1])], k, "same")[n:-n]


def current(b, what, sup, n):
    """Time [s] aligned at the event onset (I > 1 mA), supply current [A], raw volt, offset."""
    t, v = load(b, what, sup, n)
    off = v[t < t[0] + 0.2e-3].mean()
    i = (v - off) / R_SER if what == "shunt" else (off - v) / R_SER
    dt = np.median(np.diff(t))
    t_on = t[int(np.argmax(smooth(i, dt) > 1e-3))]
    return t - t_on, i, v, off


def tail_tau(t, i, dt):
    """Exponential fit to the decay after the peak, 70 % to 10 % of the peak (smoothed)."""
    s = smooth(i, dt)
    j = int(np.argmax(s))
    p = s[j]
    after = s[j:]
    a = j + int(np.argmax(after < 0.7 * p))
    e = j + int(np.argmax(after < 0.1 * p))
    if e <= a + 5:
        return np.nan
    sl, _ = np.polyfit(t[a:e], np.log(s[a:e]), 1)
    return -1 / sl


def metrics(b, what, sup, n):
    t, i, v, off = current(b, what, sup, n)
    dt = np.median(np.diff(t))
    s = smooth(i, dt)
    tau = tail_tau(t, i, dt) if b != "B1" else np.nan   # B #1 has no RC tail, the fit there means nothing
    i_end = s[-int(round(0.1e-3 / dt)):].mean()
    q_tail = max(i_end, 0) * (tau if np.isfinite(tau) else 0)
    above = np.nonzero(s > 1e-3)[0]
    m = dict(board=b, what=what, supply=sup, V_supply=SUPPLY[sup], rep=n, file=fname(b, what, sup, n),
             dt_us=dt * 1e6, n=len(t), offset_mV=off * 1e3, noise_uA=i[t < t[0] + 0.2e-3].std() * 1e6,
             I_peak_mA=s.max() * 1e3, Q_uC=(np.trapezoid(i, t) + q_tail) * 1e6, Q_tail_uC=q_tail * 1e6,
             E_uJ=(SUPPLY[sup] * np.trapezoid(i, t) - R_SER * np.trapezoid(i ** 2, t)) * 1e6,
             t_event_ms=(t[above[-1]] - t[above[0]]) * 1e3, tau_us=tau * 1e6, C_uF=tau / R_SER * 1e6,
             I_end_uA=i_end * 1e6)
    if what == "vdd":
        m.update(V_base=off, V_min_raw=v.min(), dV_mV=s.max() * R_SER * 1e3,
                 V_min_smooth=off - s.max() * R_SER)
    return m


def lpf(x, tau, dt):
    a = dt / (tau + dt)
    return lfilter([a], [1, -(1 - a)], x, zi=[x[0] * (1 - a)])[0]


def rc_fit(b, sup, n, n_tmpl):
    tc, ic, _, _ = current(b, "shunt", sup, n)
    t0, i0, _, _ = current("B1", "shunt", sup, n_tmpl)
    dt = np.median(np.diff(tc))
    t0r = np.arange(t0[0], t0[-1], dt)          # template on the capture's sample step
    i0r = np.interp(t0r, t0, i0)

    def model(p):
        k, lt, sh = p
        return k * lpf(np.interp(tc - sh, t0r, i0r, left=0, right=0), np.exp(lt), dt)

    best = None
    for lt0 in np.log([100e-6, 300e-6, 1e-3, 3e-3]):
        r = least_squares(lambda p: model(p) - ic, [1, lt0, 0],
                          bounds=([0.3, np.log(1e-6), -3e-3], [3, np.log(2e-2), 3e-3]), x_scale=[0.1, 0.3, 1e-4])
        if best is None or r.cost < best.cost:
            best = r
    k, lt, sh = best.x
    return dict(board=b, supply=sup, rep=n, k=k, tau_us=np.exp(lt) * 1e6, C_uF=np.exp(lt) / R_SER * 1e6,
                shift_us=sh * 1e6, rms_uA=np.sqrt(np.mean(best.fun ** 2)) * 1e6, t=tc, meas=ic, model=model(best.x))


# ---------------------------------------------------------------- metrics table
rows = [metrics(b, w, s, n) for (w, s) in CONDS for b in BOARDS for n in range(1, N_REP + 1)]
cols = ["file", "board", "what", "supply", "V_supply", "rep", "dt_us", "n", "offset_mV", "I_peak_mA", "Q_uC",
        "Q_tail_uC", "E_uJ", "t_event_ms", "noise_uA", "tau_us", "C_uF", "I_end_uA", "V_base", "V_min_raw", "V_min_smooth", "dV_mV"]
with open(os.path.join(OUT, "vdd_sag_summary.csv"), "w", encoding="utf-8") as f:
    f.write(",".join(cols) + "\n")
    for m in rows:
        f.write(",".join(f"{m[c]:.6g}" if isinstance(m.get(c), (float, np.floating)) else str(m.get(c, ""))
                         for c in cols) + "\n")


def sel(b, w, s):
    return [m for m in rows if m["board"] == b and m["what"] == w and m["supply"] == s]


def ms(x, fmt="{:.2f}"):
    x = np.asarray(x, float)
    if np.all(np.isnan(x)):
        return "-"
    return (fmt + " ± " + fmt).format(np.nanmean(x), np.nanstd(x, ddof=1))


print(f"R = {R_SER} ohm. Means of 5 captures ± sample std.\n")
print(f"{'board':9} {'what':5} {'supply':6} {'I_peak mA':>16} {'Q uC':>16} {'E uJ':>16} {'t_event ms':>15} {'tau us':>14} "
      f"{'C uF':>14} {'dV mV':>14}")
for (w, s) in CONDS:
    for b in BOARDS:
        g = sel(b, w, s)
        dv = ms([m["dV_mV"] for m in g], "{:.1f}") if w == "vdd" else ""
        print(f"{b:9} {w:5} {s:6} {ms([m['I_peak_mA'] for m in g]):>16} {ms([m['Q_uC'] for m in g]):>16} "
              f"{ms([m['E_uJ'] for m in g]):>16} {ms([m['t_event_ms'] for m in g]):>15} {ms([m['tau_us'] for m in g], '{:.0f}'):>14} "
              f"{ms([m['C_uF'] for m in g], '{:.1f}'):>14} {dv:>14}")

fits = [rc_fit(b, s, n, n) for b in ["B2", "B3"] for s in SUPPLY for n in range(1, N_REP + 1)]
print("\nRC fits against B #1 at the same supply (k = charge ratio, C = tau / R):")
for b in ["B2", "B3"]:
    for s in SUPPLY:
        g = [f for f in fits if f["board"] == b and f["supply"] == s]
        print(f"  {b} {s}: tau {ms([f['tau_us'] for f in g], '{:.0f}')} us, C {ms([f['C_uF'] for f in g], '{:.1f}')} uF,"
              f" k {ms([f['k'] for f in g], '{:.3f}')}, rms {ms([f['rms_uA'] for f in g], '{:.0f}')} uA")

# ---------------------------------------------------------------- figure 1: current per supply voltage
fig, axs = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
for a, s in zip(axs, SUPPLY):
    for b in BOARDS:
        t, i, _, _ = current(b, "shunt", s, SHOW)
        g = sel(b, "shunt", s)
        a.plot(t * 1e3, i * 1e3, color=COL[b], ls=LS[b], lw=1.0,
               label=f"{LABEL[b]}: peak {np.mean([m['I_peak_mA'] for m in g]):.1f} mA, "
                     f"{np.mean([m['Q_uC'] for m in g]):.1f} µC")
    a.set(title=f"Supply {SUPPLY[s]:.3f} V through {R_SER} Ω", xlabel="time from event onset [ms]", xlim=(-0.5, 12))
    a.legend(loc="upper right", fontsize=7.5)
axs[0].set_ylabel("supply current [mA]")
fig.suptitle("Supply current during one advert (capture 3 of 5 shown, peak and charge are means of 5), 2026-11-26")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "vdd_sag_current.png"), dpi=150)

# ---------------------------------------------------------------- figure 2: VDD at 2.0 V and cross-check
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.8))
for b in BOARDS:
    t, i, v, off = current(b, "vdd", "2V0", SHOW)
    g = sel(b, "vdd", "2V0")
    a1.plot(t * 1e3, v, color=COL[b], ls=LS[b], lw=1.0,
            label=f"{LABEL[b]}: dip {ms([m['dV_mV'] for m in g], '{:.1f}')} mV")
    ts, i_s, _, _ = current(b, "shunt", "2V0", SHOW)
    a2.plot(ts * 1e3, i_s * 1e3, color=COL[b], ls="-", lw=0.8, alpha=0.6)
    a2.plot(t * 1e3, smooth(i, np.median(np.diff(t))) * 1e3, color=COL[b], ls=LS[b], lw=1.2, label=SHORT[b])
a1.set(title=f"VDD at the board, supply {SUPPLY['2V0']:.4f} V through {R_SER} Ω",
       xlabel="time from event onset [ms]", ylabel="VDD [V]", xlim=(-0.5, 12))
a1.legend(loc="lower right", fontsize=8)
a2.set(title="Current from the VDD drop (dashed / dotted, 50 µs average)\nagainst the shunt capture (thin solid)",
       xlabel="time from event onset [ms]", ylabel="supply current [mA]", xlim=(-0.5, 12))
a2.legend(loc="upper right", fontsize=8)
fig.suptitle("VDD sag at 2.0 V supply (capture 3 of 5 shown), 2026-11-26")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "vdd_sag_vdd.png"), dpi=150)

# ---------------------------------------------------------------- figure 3: all repeats
fig, axs = plt.subplots(4, 4, figsize=(15, 11), sharex=True)
for c, (w, s) in enumerate(CONDS):
    for r, b in enumerate(BOARDS):
        a = axs[r][c]
        for n in range(1, N_REP + 1):
            t, i, v, off = current(b, w, s, n)
            y = v if w == "vdd" else i * 1e3
            a.plot(t * 1e3, y, color=COL[b], lw=0.5, alpha=0.8)
        g = sel(b, w, s)
        txt = (f"dip {ms([m['dV_mV'] for m in g], '{:.1f}')} mV" if w == "vdd"
               else f"peak {ms([m['I_peak_mA'] for m in g])} mA\nQ {ms([m['Q_uC'] for m in g])} µC")
        a.text(0.98, 0.05 if w == "vdd" else 0.95, txt, transform=a.transAxes, ha="right",
               va="bottom" if w == "vdd" else "top", fontsize=7.5)
        if r == 0:
            a.set_title(f"{'VDD' if w == 'vdd' else 'current'}, supply {SUPPLY[s]:.3f} V")
        if c == 0:
            a.set_ylabel(f"{SHORT[b]}\ncurrent [mA]")
        if c == 3:
            a.set_ylabel("VDD [V]")
        a.set_xlim(-1, 12)
for a in axs[-1]:
    a.set_xlabel("time from event onset [ms]")
fig.suptitle("All 80 captures, 5 repeats overlaid per board and condition, 2026-11-26")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "vdd_sag_repeats.png"), dpi=150)

# ---------------------------------------------------------------- figure 4: metrics against supply voltage
fig, axs = plt.subplots(1, 3, figsize=(15, 4.4))
for b in BOARDS:
    vs = [SUPPLY[s] for s in SUPPLY]
    for a, key in zip(axs[:2], ["I_peak_mA", "Q_uC"]):
        y = [[m[key] for m in sel(b, "shunt", s)] for s in SUPPLY]
        a.errorbar(vs, [np.mean(x) for x in y], yerr=[np.std(x, ddof=1) for x in y], color=COL[b], ls=LS[b],
                   marker=MK[b], ms=6, lw=1.2, capsize=3, label=LABEL[b])
    g = sel(b, "vdd", "2V0")
    axs[2].bar(BOARDS.index(b), np.mean([m["dV_mV"] for m in g]), color=COL[b], width=0.6,
               yerr=np.std([m["dV_mV"] for m in g], ddof=1), capsize=3)
    axs[2].text(BOARDS.index(b), np.mean([m["dV_mV"] for m in g]) + 8, f"{np.mean([m['dV_mV'] for m in g]):.0f} mV",
                ha="center", fontsize=8)
axs[0].set(xlabel="supply voltage [V]", ylabel="peak supply current [mA] (50 µs average)")
axs[1].set(xlabel="supply voltage [V]", ylabel="charge per event [µC]")
axs[2].set(ylabel=f"VDD dip [mV] (supply 2.0 V, {R_SER} Ω)", title="VDD dip")
axs[2].set_xticks(range(len(BOARDS)), [LABEL[b].replace(", ", "\n") for b in BOARDS], fontsize=8)
axs[2].grid(axis="x", visible=False)
for a in axs[:2]:
    a.set_ylim(bottom=0)
    a.legend(fontsize=7.5, loc="lower left")
axs[0].set_title("Peak current")
axs[1].set_title("Charge per event")
fig.suptitle("Means of 5 captures, error bars ± 1 sample std, 2026-11-26")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "vdd_sag_metrics.png"), dpi=150)

# ---------------------------------------------------------------- figure 5: RC fit at 2.0 V
fig, axs = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
for a, b in zip(axs, ["B2", "B3"]):
    f = next(x for x in fits if x["board"] == b and x["supply"] == "2V0" and x["rep"] == 3)
    a.plot(f["t"] * 1e3, f["meas"] * 1e3, color=COL[b], lw=0.7, label=f"{LABEL[b]}, measured")
    a.plot(f["t"] * 1e3, f["model"] * 1e3, color="0.15", lw=1.0, ls="--", label="B #1 current, low-passed")
    a.set(title=f"{LABEL[b]}: tau {f['tau_us']:.0f} µs, C = tau / R {f['C_uF']:.0f} µF, k {f['k']:.2f}, "
                f"rms {f['rms_uA']:.0f} µA", xlabel="time from event onset [ms]", xlim=(-0.5, 12))
    a.legend(loc="upper right", fontsize=8)
axs[0].set_ylabel("supply current [mA]")
fig.suptitle(f"RC model at 2.0 V supply (capture 3): current with bulk C = k x low-pass (tau = R C) of the B #1 current")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "vdd_sag_rc_fit.png"), dpi=150)
print("\nwrote figures and vdd_sag_summary.csv to", OUT)

import numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import sys, glob
R = sys.argv[1]; OUT = sys.argv[2]
M = R + "/testing/rev_B/RF/"; S = R + "/testing/RF/antenna_C23-B/data/"
def vna(n):
    f = glob.glob(M + "s11_%s_*.csv" % n)[0]
    d = np.genfromtxt(f, delimiter=",", skip_header=6, skip_footer=1)
    d = d[~np.isnan(d).any(axis=1)]
    return d[:,0], d[:,1] + 1j*d[:,2]
def sim(n):
    d = np.genfromtxt(S + n, delimiter=",", names=True)
    return d["f_Hz"], d["Zin_re_ohm"] + 1j*d["Zin_im_ohm"]
G = lambda z: (z-50)/(z+50); dB = lambda z: 20*np.log10(np.abs(G(z)))
BAND = (2.400, 2.4835)
def ax_s11(ax, title, lo=2.0, hi=3.0):
    ax.axvspan(*BAND, color="0.88", zorder=0); ax.axhline(-10, color="0.5", ls=":", lw=1)
    ax.set_xlim(lo, hi); ax.set_ylim(-45, 0); ax.set_xlabel("Frequency (GHz)"); ax.set_ylabel("|S11| (dB)")
    ax.set_title(title, fontsize=11); ax.grid(alpha=.3)
figs = []
# 1 matched B2 conditions
fig, ax = plt.subplots(figsize=(8,4.8))
for n, lab in [("08","in air, cell"),("05","in air"),("07","on holder, cell"),("04","on holder"),("06","flat on table")]:
    f, z = vna(n); ax.plot(f/1e9, dB(z), label=f"file {n}: {lab}")
ax_s11(ax, "B #2 with L2 1.6 nH / L3 6.8 nH, measured at J2 (13 Nov 2026)")
ax.legend(fontsize=8, loc="lower left"); figs.append((fig, "1_B2_matched_conditions"))
# 2 unmatched B1
fig, ax = plt.subplots(figsize=(8,4.8))
for n, lab in [("10","in air, cell"),("09","on holder, cell"),("03","on holder")]:
    f, z = vna(n); ax.plot(f/1e9, dB(z), label=f"file {n}: {lab}")
ax_s11(ax, "B #1 antenna without parts (L2 0 Ω, L3 open), measured at J2")
ax.legend(fontsize=8, loc="lower left"); figs.append((fig, "2_B1_unmatched_conditions"))
# 3 sim vs meas
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11,4.5))
f, z = sim("s11_no_parts.csv"); a1.plot(f/1e9, dB(z), "--", label="simulated")
f, z = vna("10"); a1.plot(f/1e9, dB(z), label="measured, B #1 file 10")
ax_s11(a1, "Without parts, in air with cell", 2.2, 2.8); a1.legend(fontsize=8, loc="lower left")
f, z = sim("s11_matched_cascade.csv"); a2.plot(f/1e9, dB(z), "--", label="simulated, cascade")
f, z = sim("s11_matched_fdtd.csv"); a2.plot(f/1e9, dB(z), ":", label="simulated, full wave")
f, z = vna("08"); a2.plot(f/1e9, dB(z), label="measured, B #2 file 08")
ax_s11(a2, "L2 1.6 nH / L3 6.8 nH, in air with cell", 2.2, 2.8); a2.set_ylim(-55, 0); a2.legend(fontsize=8, loc="lower left")
fig.suptitle("openEMS simulation against VNA measurement"); fig.tight_layout(); figs.append((fig, "3_sim_vs_measured"))
# 4 matching on paper vs measured
f, za = vna("10"); w = 2*np.pi*f
def lmatch(zant, Ls, Lsh=None, Csh=None):
    z1 = zant + 1j*w*Ls; y = 1/z1 + (1j*w*Csh if Csh else 1/(1j*w*Lsh)); return 1/y
fig, ax = plt.subplots(figsize=(8,4.8))
ax.plot(f/1e9, dB(za), color="0.6", label="B #1 without parts, measured (file 10)")
ax.plot(f/1e9, dB(lmatch(za, 2.935e-9, Csh=1.305e-12)), "--", label="hand L-match: 2.935 nH series, 1.305 pF shunt (on paper)")
ax.plot(f/1e9, dB(lmatch(za, 1.6e-9, Lsh=6.8e-9)), "--", label="fitted values 1.6 nH / 6.8 nH (on paper)")
fm, zm = vna("08"); ax.plot(fm/1e9, dB(zm), label="fitted values, measured on B #2 (file 08)")
ax_s11(ax, "Matching: on paper (ideal parts on B #1 data) against measured", 2.2, 2.8); ax.set_ylim(-50,0)
ax.legend(fontsize=8, loc="lower left")
ax.text(0.99, 0.97, "on paper: shunt at J2, series to the antenna, ideal parts.\nGap between paper and measured not investigated.",
        transform=ax.transAxes, ha="right", va="top", fontsize=7, color="0.3")
figs.append((fig, "4_matching_paper_vs_measured"))
# 5 smith
fig, ax = plt.subplots(figsize=(7,7))
t = np.linspace(0, 2*np.pi, 400)
for r in [0, .2, .5, 1, 2, 5]:
    c = r/(1+r); rad = 1/(1+r); ax.plot(c+rad*np.cos(t), rad*np.sin(t), color="0.85", lw=.7)
for x in [.2, .5, 1, 2, 5]:
    for s in (1,-1):
        g = G(50*(np.logspace(-3, 3, 600) + 1j*s*x)); ax.plot(g.real, g.imag, color="0.85", lw=.7)
ax.axhline(0, color="0.85", lw=.7)
for r in [.2, .5, 1, 2, 5]:
    g = G(50*r); ax.text(g.real - 0.01, 0.015, f"{50*r:g} Ω", fontsize=7, color="0.4", rotation=90, ha="right", va="bottom")
for x in [.2, .5, 1, 2, 5]:
    for s in (1,-1):
        g = G(50*(1e-6 + 1j*s*x))
        ax.text(1.09*g.real, 1.09*g.imag, f"{'+' if s>0 else '−'}j{50*x:g} Ω", fontsize=7, color="0.4", ha="center", va="center")
ax.text(-1.15, 1.15, "Z0 = 50 Ω\nresistance and reactance labels in ohms", fontsize=8, color="0.3", va="top")
for (fr, z, lab) in [(*vna("10"), "B #1 without parts, meas."), (*sim("s11_no_parts.csv"), "without parts, sim."),
                     (*vna("08"), "B #2 matched, meas."), (*sim("s11_matched_cascade.csv"), "matched, sim. cascade")]:
    k = (fr >= 2.3e9) & (fr <= 2.6e9); g = G(z[k]); ax.plot(g.real, g.imag, label=lab)
    b = (fr >= 2.4e9) & (fr <= 2.4835e9); gb = G(z[b]); ax.plot(gb.real, gb.imag, lw=3.5, color=ax.lines[-1].get_color())
ax.set_aspect("equal"); ax.set_xlim(-1.2,1.2); ax.set_ylim(-1.2,1.2); ax.axis("off")
ax.set_title("Smith chart, 2.3–2.6 GHz (thick: BLE band), in air with cell", fontsize=10)
ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=2, frameon=False); figs.append((fig, "5_smith"))
# 6 overview for the root README: bare antenna sim vs meas, matched board in its typical placement
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11,4.5))
f, z = sim("s11_no_parts.csv"); a1.plot(f/1e9, dB(z), "--", label="simulated (openEMS)")
f, z = vna("10"); a1.plot(f/1e9, dB(z), label="measured, B #1")
ax_s11(a1, "Antenna without matching parts, in air with cell", 2.2, 2.8); a1.set_ylim(-30, 0)
a1.legend(fontsize=8, loc="lower left")
f, z = vna("07"); a2.plot(f/1e9, dB(z), color="C2", label="measured, B #2")
ax_s11(a2, "With L2 1.6 nH / L3 6.8 nH, on its battery holder with cell", 2.2, 2.8)
a2.legend(fontsize=8, loc="lower left")
fig.suptitle("BSN-C23-B printed antenna, S11 at J2"); fig.tight_layout(); figs.append((fig, "6_readme_antenna"))
with PdfPages(OUT + "/C23-B_VNA_2026-11-13.pdf") as pdf:
    for fg, n in figs:
        fg.savefig(OUT + f"/{n}.png", dpi=150, bbox_inches="tight"); pdf.savefig(fg, bbox_inches="tight")
print("ok")

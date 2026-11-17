"""Quick plots of the FPH spectrum analyser files of 2026-11-17 (B #3, cwtest +8 dBm, conducted at J2).

Run: python spectrum.py <path to testing/rev_B/RF> <out dir>
Not report style, for checking the traces against what was seen on the screen.
"""
import sys, os, glob
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load(path):
    head, f, p = {}, [], []
    for line in open(path, encoding="utf-8-sig"):
        c = line.strip().split(",")
        if not c[0]:
            continue
        if c[0][0].isdigit():
            f.append(float(c[0])); p.append(float(c[1]))
        elif len(c) >= 2:
            head[c[0]] = c[1]
    return head, f, p


def settings(h):
    return (f"span {float(h['Span'])/1e3:g} kHz, RBW {float(h['RBW'])/1e3:g} kHz, "
            f"ATT {h['RF Attenuator']} dB, {h['Trace Mode']}")


src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
files = {os.path.basename(x)[:5]: x for x in glob.glob(os.path.join(src, "sa_*.csv"))}

# Carriers
fig, axs = plt.subplots(2, 2, figsize=(12, 8))
for ax, key in zip(axs.flat, ["sa_01", "sa_02", "sa_03", "sa_19"]):
    h, f, p = load(files[key])
    fc = float(h["Center Frequency"])
    x = [(v - fc) / 1e3 for v in f]
    i = max(range(len(p)), key=p.__getitem__)
    ax.plot(x, p, lw=0.8)
    ax.plot(x[i], p[i], "rv")
    ax.annotate(f"{f[i]/1e6:.6f} MHz\n{p[i]:+.2f} dBm ({x[i]:+.2f} kHz)", (x[i], p[i]),
                xytext=(10, -30), textcoords="offset points", fontsize=9)
    ax.set_title(f"{os.path.basename(files[key])}\n{settings(h)}", fontsize=9)
    ax.set_xlabel(f"offset from {fc/1e6:g} MHz [kHz]")
    ax.set_ylabel("dBm")
    ax.set_ylim(-80, 15)
    ax.grid(alpha=0.3)
fig.suptitle("B #3 cwtest +8 dBm, carrier at J2 (probe and cable loss not corrected)")
fig.tight_layout()
fig.savefig(os.path.join(out, "6_carriers.png"), dpi=130)

# Harmonics, rows = carrier, columns = H1..H5
fig, axs = plt.subplots(3, 5, figsize=(20, 10), sharey=True)
for r, start in enumerate([4, 9, 14]):
    for c in range(5):
        key = f"sa_{start + c:02d}"
        h, f, p = load(files[key])
        fc = float(h["Center Frequency"])
        x = [(v - fc) / 1e3 for v in f]
        i = max(range(len(p)), key=p.__getitem__)
        ax = axs[r][c]
        ax.plot(x, p, lw=0.7)
        ax.plot(x[i], p[i], "rv")
        if c > 0:
            ax.axhline(-41.2, color="r", ls="--", lw=0.8)
        ax.set_title(f"{key} H{c+1} {fc/1e6:g} MHz\npeak {p[i]:+.1f} dBm at {x[i]:+.0f} kHz", fontsize=8)
        ax.set_ylim(-80, 10)
        ax.grid(alpha=0.3)
        if r == 2:
            ax.set_xlabel("offset [kHz]")
        if c == 0:
            ax.set_ylabel("dBm")
fig.suptitle("B #3 cwtest +8 dBm, harmonics at J2. Rows: 2402, 2440, 2480 MHz. "
             f"{settings(h)}. Red dashed: -41.2 dBm FCC restricted band (EIRP, used as stand-in)")
fig.tight_layout()
fig.savefig(os.path.join(out, "7_harmonics.png"), dpi=110)
print("done")

"""CR2032 voltage under CW load, B #3, 2026-11-17. Two settings (0 and +8 dBm), hold then recovery.

Run: python voltage_hold.py [out dir]   (default: this folder)
Dots mark the measured points, only a few samples were taken.
"""
import sys, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# (minutes, volts). Hold is measured from carrier-on at t=0. "caps charged" open-circuit shown as a marker at t=0-.
hold = {
    "+8 dBm (14.2 mA)": {
        "oc": 3.282,
        "t": [0, 3, 6, 9, 12, 15],
        "v": [2.950, 2.744, 2.650, 2.599, 2.575, 2.563],
        "rec_t": [1.0, 3.0, 6.0, 15.0],
        "rec_v": [2.800, 2.868, 2.898, 2.937],
        "c": "#c1432e",
    },
    "0 dBm (6.1 mA)": {
        "oc": 3.286,
        "t": [0, 3, 6, 9.5, 12, 15],
        "v": [3.170, 2.912, 2.855, 2.807, 2.781, 2.762],
        "rec_t": [1.5, 3.0, 6.0, 15.0],
        "rec_v": [2.898, 2.918, 2.939, 2.970],
        "c": "#2f6ead",
    },
}

out = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))

fig, (axh, axr) = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True,
                               gridspec_kw={"width_ratios": [3, 2]})

for name, d in hold.items():
    axh.plot(d["t"], d["v"], "-o", color=d["c"], ms=6, label=name)
    axh.plot(-0.6, d["oc"], "D", color=d["c"], ms=7)  # open-circuit before load
    axh.annotate(f"{d['oc']:.3f} V", (-0.6, d["oc"]), xytext=(4, 6),
                 textcoords="offset points", fontsize=8, color=d["c"])
    axh.annotate(f"{d['v'][-1]:.3f} V", (d["t"][-1], d["v"][-1]), xytext=(6, -2),
                 textcoords="offset points", fontsize=8, color=d["c"])
    axr.plot(d["rec_t"], d["rec_v"], "-o", color=d["c"], ms=6, label=name)

axh.set_title("Under CW load (carrier on at t = 0)")
axh.set_xlabel("time under load [min]")
axh.set_ylabel("CR2032 terminal voltage [V]")
axh.set_xlim(-1.5, 16)
axh.grid(alpha=0.3)
axh.legend(loc="upper right", fontsize=9)
axh.text(-0.6, 3.05, "open\ncircuit", fontsize=7, ha="center", color="0.4")

axr.set_title("Recovery (load removed at 15 min)")
axr.set_xlabel("time after unload [min]")
axr.set_xlim(0, 16)
axr.grid(alpha=0.3)

fig.suptitle("B #3 CR2032 (RS no-brand) voltage under CW load, 2026-11-17. Dots = measured points")
fig.tight_layout()
p = os.path.join(out, "voltage_hold.png")
fig.savefig(p, dpi=140)
print("wrote", p)

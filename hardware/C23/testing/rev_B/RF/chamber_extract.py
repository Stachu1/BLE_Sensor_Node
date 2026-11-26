"""Extract the numbers from the chamber report PDFs of 2026-11-19 (rev A and rev B).

Writes, next to this script:
  chamber_2026-11-19_pattern.csv  one row per (report, frequency, azimuth, elevation): total EIRP in dBm
  chamber_2026-11-19_summary.csv  one row per (report, frequency): the "OTA Evaluation Results" of the report
                                  (empty where the report has no summary page, e.g. the 4880/9760 MHz files),
                                  plus TRP / peak / min / average recomputed from the grid as a check
  chamber_2026-11-19.json         the same, nested, with the run metadata

The tables are read by word position (PyMuPDF), not from the text flow, so the columns cannot shift.
Run: python chamber_extract.py
"""
import csv
import json
import math
import re
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
REV_A = HERE.parent.parent / "rev_A" / "RF" / "chamber_2026-11-19"
REV_B = HERE / "chamber_2026-11-19"

# Board / run / validity as in CHAMBER.md
REPORTS = [
    (REV_B / "ch_01_B2_2400-7200-12000MHz_wrong-freq.pdf", "C23-B", "B2", "pi fitted", "11:57-12:25", False),
    (REV_B / "ch_02_B2_4800MHz_wrong-freq.pdf", "C23-B", "B2", "pi fitted", "11:57-12:25", False),
    (REV_B / "ch_03_B2_9600MHz_wrong-freq.pdf", "C23-B", "B2", "pi fitted", "11:57-12:25", False),
    (REV_A / "ch_01_A1_2440-7320-12200MHz.pdf", "C23-A", "A1", "as built", "13:00-13:24", True),
    (REV_A / "ch_02_A1_4880MHz.pdf", "C23-A", "A1", "as built", "13:00-13:24", True),
    (REV_A / "ch_03_A1_9760MHz.pdf", "C23-A", "A1", "as built", "13:00-13:24", True),
    (REV_B / "ch_04_B2_no-pi_2400-7200-12000MHz_wrong-freq.pdf", "C23-B", "B2", "pi removed", "13:39-14:03", False),
    (REV_B / "ch_05_B9_2440-7320-12200MHz.pdf", "C23-B", "B9", "pi fitted", "14:13-14:37", True),
    (REV_B / "ch_06_B9_4880MHz.pdf", "C23-B", "B9", "pi fitted", "14:13-14:37", True),
    (REV_B / "ch_07_B9_9760MHz.pdf", "C23-B", "B9", "pi fitted", "14:13-14:37", True),
]

NUM = re.compile(r"^-?\d+(?:[.,]\d+)?$")
TITLE = re.compile(r"^\"?RP_(\d+\.\d+)_tot\"?$")


def num(s):
    return float(s.replace(",", "."))


def rows_of(words, tol=2.0):
    """Group words into lines by y, each line sorted by x."""
    lines = []
    for w in sorted(words, key=lambda w: (w[1], w[0])):
        if lines and abs(lines[-1][0] - w[1]) < tol:
            lines[-1][1].append(w)
        else:
            lines.append([w[1], [w]])
    return [(y, sorted(ws, key=lambda w: w[0])) for y, ws in lines]


def parse_tables(doc):
    """Return {freq_MHz: {(az, el): dBm}} from all RP_<f>_tot tables (main part and continuation)."""
    tables = {}
    for page in doc:
        lines = rows_of(page.get_text("words"))
        freq = None
        cols = None  # list of (x_center, elevation)
        for y, ws in lines:
            texts = [w[4] for w in ws]
            m = TITLE.match(texts[0]) if texts else None
            if m:
                freq = float(m.group(1))
                cols = None
                continue
            if "continuation" in texts[0]:
                m = next((TITLE.match(t) for t in texts if TITLE.match(t)), None)
                freq = float(m.group(1))
                cols = None
                continue
            if freq is None:
                continue
            # header line with the elevations: "(deg) 0 deg 20 deg ... "
            if texts[0] == "(deg)":
                cols = []
                for i, w in enumerate(ws[1:], 1):
                    if NUM.match(w[4]) and i + 1 < len(ws) and ws[i + 1][4] == "deg":
                        cols.append(((w[0] + ws[i + 1][2]) / 2, num(w[4])))
                continue
            if cols and all(NUM.match(t) for t in texts) and len(texts) == len(cols) + 1:
                az = num(texts[0])
                for w in ws[1:]:
                    xc = (w[0] + w[2]) / 2
                    el = min(cols, key=lambda c: abs(c[0] - xc))[1]
                    key = (az, el)
                    assert key not in tables.setdefault(freq, {}), (freq, key)
                    tables[freq][key] = num(w[4])
    return tables


SUMMARY_KEYS = {
    "Total Radiated Power": ("trp_dBm", "dBm"),
    "Directivity": ("directivity_dBi", "dBi"),
    "Total Efficiency": ("total_eff_dB", "dB"),  # and % (second line)
    "Peak EIRP": ("peak_eirp_dBm", "dBm"),
    "UHRP": ("uhrp_dBm", "dBm"),
    "PGRP (0-120°)": ("pgrp_0_120_dBm", "dBm"),
    "Front/Back Ratio": ("front_back_ratio", ""),
    "PhiBW": ("phi_bw_deg", "deg"),
    "ThetaBW": ("theta_bw_deg", "deg"),
    "ThetaBW Up": ("theta_bw_up_deg", "deg"),
    "ThetaBW Down": ("theta_bw_down_deg", "deg"),
    "Boresight Phi": ("boresight_phi_deg", "deg"),
    "Boresight Theta": ("boresight_theta_deg", "deg"),
    "Maximum Power": ("max_power_dBm", "dBm"),
    "Minimum Power": ("min_power_dBm", "dBm"),
    "Average Power": ("avg_power_dBm", "dBm"),
    "Max/Min Ratio": ("max_min_ratio_dB", "dB"),
    "Max/Avg Ratio": ("max_avg_ratio_dB", "dB"),
    "Min/Avg Ratio": ("min_avg_ratio_dB", "dB"),
    "Worst Single Value": ("worst_single_dBm", "dBm"),
    "Best Single Value": ("best_single_dBm", "dBm"),
}


def parse_summaries(doc):
    """Return {freq_MHz: {field: value}} from the 'OTA Test Results for Frequency' pages."""
    out = {}
    for page in doc:
        text = page.get_text("text")
        m = re.search(r"OTA Test Results for Frequency ([\d.]+) MHz", text)
        if not m:
            continue
        freq = float(m.group(1))
        s = {}
        lines = rows_of(page.get_text("words"))
        for y, ws in lines:
            # label = words left of x 200, value = first number right of it
            label = " ".join(w[4] for w in ws if w[0] < 200)
            vals = [w[4] for w in ws if w[0] >= 200]
            if not vals or not NUM.match(vals[0]):
                continue
            label = label.replace("�", "°")
            if label not in SUMMARY_KEYS:
                continue
            key, unit = SUMMARY_KEYS[label]
            v = num(vals[0])
            if label == "Total Efficiency" and len(vals) > 1 and vals[1] == "%":
                key = "total_eff_pct"
            if key in s:
                continue
            s[key] = v
        for name, pat in [("worst_position", r"Worst Position\s+(.+)"), ("best_position", r"Best Position\s+(.+)")]:
            mm = re.search(pat, text)
            if mm:
                s[name] = mm.group(1).strip()
        mm = re.search(r"Start: (\S+ \S+); Stop: (\S+ \S+)", text)
        if mm:
            s["start"], s["stop"] = mm.groups()
        for pol in ("Theta", "Phi"):
            mm = re.search(rf"Cal Data {pol}:\s+([\d.]+) dB", text)
            if mm:
                s[f"cal_{pol.lower()}_dB"] = float(mm.group(1))
        out[freq] = s
    return out


def grid_stats(t):
    """TRP etc. from the grid. Elevation = theta from +Z, azimuth = phi. Azimuth 360 duplicates 0 and is dropped.
    Each point gets the solid angle of its theta band (band edges halfway between the sampled thetas).
    This matches the report TRP within 0.01 dB for the flat (noise floor) patterns, but not for the 2440 MHz
    patterns (B9 -0.86 vs -0.74 dBm, A1 -5.07 vs -4.52 dBm); the lab software integrates in its own way
    (probably per polarisation, finer data). Use the report TRP as the reference."""
    els = sorted({el for _, el in t})
    azs = sorted({az for az, _ in t if az < 360})
    edges = [0.0] + [(a + b) / 2 for a, b in zip(els, els[1:])] + [180.0]
    p_sum = 0.0
    for i, el in enumerate(els):
        band = math.cos(math.radians(edges[i])) - math.cos(math.radians(edges[i + 1]))  # / 2 = fraction of sphere
        for az in azs:
            p_sum += 10 ** (t[(az, el)] / 10) * band / 2 / len(azs)
    vals = [t[(az, el)] for az in azs for el in els]
    # the report's "Average Power" is the plain linear mean of all 190 points, azimuth 360 included
    lin = [10 ** (v / 10) for v in t.values()]
    return {
        "grid_trp_sin_dBm": round(10 * math.log10(p_sum), 2),
        "grid_peak_dBm": max(vals),
        "grid_min_dBm": min(vals),
        "grid_avg_dBm": round(10 * math.log10(sum(lin) / len(lin)), 2),
        "n_points": len(t),
    }


def main():
    pattern_rows, summary_rows, nested = [], [], []
    for path, rev, board, variant, run, valid in REPORTS:
        doc = pymupdf.open(path)
        tables = parse_tables(doc)
        sums = parse_summaries(doc)
        rel = path.relative_to(HERE.parent.parent.parent).as_posix()  # relative to hardware/C23/testing
        for freq in sorted(tables):
            t = tables[freq]
            n_el = len({el for _, el in t})
            n_az = len({az for az, _ in t})
            assert (n_az, n_el) == (19, 10), (path.name, freq, n_az, n_el)
            s = sums.get(freq, {})
            g = grid_stats(t)
            meta = {
                "file": rel, "rev": rev, "board": board, "variant": variant, "run": run,
                "freq_MHz": freq, "valid": valid,
            }
            summary_rows.append({**meta, **{k: v for k, v in s.items()}, **g})
            for (az, el), v in sorted(t.items()):
                pattern_rows.append({**meta, "azimuth_deg": az, "elevation_deg": el, "eirp_dBm": v})
            nested.append({
                **meta, "summary": s, "grid_check": g,
                "elevation_deg": sorted({el for _, el in t}),
                "azimuth_deg": sorted({az for az, _ in t}),
                "eirp_dBm": [[t[(az, el)] for el in sorted({e for _, e in t})] for az in sorted({a for a, _ in t})],
            })
            print(f"{path.name:52s} {freq:9.3f} MHz  report TRP {s.get('trp_dBm', ''):>7}  grid TRP {g['grid_trp_sin_dBm']:7.2f}"
                  f"  peak {s.get('peak_eirp_dBm', ''):>6}/{g['grid_peak_dBm']:6.2f}")

    with open(HERE / "chamber_2026-11-19_pattern.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(pattern_rows[0]))
        w.writeheader()
        w.writerows(pattern_rows)
    fields = []
    for r in summary_rows:
        fields += [k for k in r if k not in fields]
    with open(HERE / "chamber_2026-11-19_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(summary_rows)
    with open(HERE / "chamber_2026-11-19.json", "w", encoding="utf-8") as f:
        json.dump({
            "source": "SDU antenna chamber reports 2026-11-19, see CHAMBER.md",
            "units": {"eirp_dBm": "total EIRP (both polarisations combined), dBm, calibrated by the lab software"},
            "axes": "elevation = theta from +Z, azimuth = phi; chamber X towards the receive antenna, Z up",
            "eirp_dBm_layout": "eirp_dBm[i_azimuth][i_elevation]; azimuth 360 repeats azimuth 0",
            "grid_check": "grid_trp_sin_dBm = sin(theta) solid-angle integration of the 20 deg table; equals the report TRP"
                          " for the flat noise-floor patterns but reads 0.12 dB (B9) and 0.55 dB (A1) low at 2440 MHz."
                          " grid_avg_dBm = linear mean of all 190 points, equals the report 'Average Power'.",
            "valid": "False for the B2 runs, measured 40 MHz off the carrier (noise floor only)",
            "measurements": nested,
        }, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()

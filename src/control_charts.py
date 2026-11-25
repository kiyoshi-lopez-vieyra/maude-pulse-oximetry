"""Trend detection: p-charts of the monthly share of a failure type.

Run from the project root:
  python src/control_charts.py                  # FDA problem terms (after build_tables.py)
  python src/control_charts.py --by predicted   # predicted failure categories (after predict_all.py)
Outputs: results/control_charts[_predicted]/<name>.png and signals.csv

With --by predicted, the denominator is the reports of the month that HAVE a description
(only those can be classified), and the charts stop at 2026-06 because many reports
received July-October 2026 had no narrative yet in this download.

Method
- For each month t: n_t = all DQA reports received, x_t = reports with the problem term.
  p_t = x_t / n_t is the share of that month's reports mentioning the problem.
- Phase I (baseline) 2020-01 to 2022-12: center line p_bar = sum(x) / sum(n).
- Limits per month (they widen when n_t is small): p_bar +/- 3 * sqrt(p_bar (1 - p_bar) / n_t).
- Phase II (monitoring) 2023-01 onward, two signal rules:
    rule 1: a point above the upper limit;
    rule 2: 8 consecutive points above the center line (sustained shift).
- Over-dispersion check (Laney p'): reports are not independent (batches, one
  manufacturer filing many similar reports), so the binomial limits can be too narrow.
  sigma_z > 1 means extra variation; signals are also tested with limits widened by sigma_z.
A signal means "look at these reports", never "the device got worse".
"""

import argparse
import csv
import math
import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "maude.db"
OUT_DIR = PROJECT_ROOT / "results" / "control_charts"
OUT_DIR_PREDICTED = PROJECT_ROOT / "results" / "control_charts_predicted"
BASELINE = ("2020-01", "2022-12")
MONITOR_START = "2023-01"
LAST_MONTH = "2026-10"   # last month fully covered by the 2026-11-24 download
LAST_MONTH_PREDICTED = "2026-06"  # later months often lack narrative text
PREDICTED = ["accuracy", "alarm", "power_battery", "patient_contact", "display",
             "signal_acquisition", "physical_damage", "software_behavior"]
PROBLEMS = [
    "Incorrect Measurement",
    "Low Readings",
    "High Readings",
    "Device Alarm System",
    "Sensing Intermittently",
    "Unexpected Shutdown",
]

# Colors from the dataviz reference palette; signals also get a different marker and a label.
INK, MUTED, GRID, LINE, SIGNAL, SURFACE = "#0b0b0b", "#898781", "#e1e0d9", "#2a78d6", "#d03b3b", "#fcfcfb"


def months_between(start, end):
    y, m = int(start[:4]), int(start[5:])
    out = []
    while f"{y:04d}-{m:02d}" <= end:
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def analyze(months, n, x):
    base = [i for i, mth in enumerate(months) if BASELINE[0] <= mth <= BASELINE[1] and n[i] > 0]
    p_bar = sum(x[i] for i in base) / sum(n[i] for i in base)
    sd = [math.sqrt(p_bar * (1 - p_bar) / k) if k else float("nan") for k in n]
    # Laney sigma_z from the baseline z-scores (average moving range / 1.128)
    z = [(x[i] / n[i] - p_bar) / sd[i] for i in base if sd[i] > 0]
    mr = [abs(a - b) for a, b in zip(z[1:], z[:-1])]
    sigma_z = (sum(mr) / len(mr)) / 1.128 if mr else 1.0
    return p_bar, sd, sigma_z


def find_signals(months, n, x, p_bar, sd, sigma_z):
    signals, run = [], 0
    for i, mth in enumerate(months):
        if mth < MONITOR_START or n[i] == 0:
            continue
        p = x[i] / n[i]
        run = run + 1 if p > p_bar else 0
        if p > p_bar + 3 * sd[i]:
            survives = p > p_bar + 3 * sd[i] * max(sigma_z, 1.0)
            signals.append((mth, "rule1_above_UCL", round(p, 3), survives))
        if run == 8:
            signals.append((mth, "rule2_8_above_center", round(p, 3), True))
    return signals


def plot(problem, months, n, x, p_bar, sd, signals, out_dir, footnote, noun):
    idx = [i for i in range(len(months)) if n[i] > 0]
    p = [x[i] / n[i] for i in idx]
    ucl = [p_bar + 3 * sd[i] for i in idx]
    lcl = [max(0.0, p_bar - 3 * sd[i]) for i in idx]
    fig, ax = plt.subplots(figsize=(10, 4), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    ax.step(idx, ucl, where="mid", color=MUTED, lw=1, ls="--")
    ax.step(idx, lcl, where="mid", color=MUTED, lw=1, ls="--")
    ax.axhline(p_bar, color=MUTED, lw=1)
    ax.plot(idx, p, color=LINE, lw=2, marker="o", ms=3.5)
    strong = {s[0] for s in signals if s[1] == "rule1_above_UCL" and s[3]}
    weak = {s[0] for s in signals if s[1] == "rule1_above_UCL" and not s[3]}
    sx = [i for i in idx if months[i] in strong]
    wx = [i for i in idx if months[i] in weak]
    ax.scatter(sx, [x[i] / n[i] for i in sx], s=70, marker="D", color=SIGNAL, zorder=5,
               edgecolor=SURFACE, linewidth=1.5, label="Above limit (also with Laney limits)")
    ax.scatter(wx, [x[i] / n[i] for i in wx], s=60, marker="D", facecolor=SURFACE, zorder=5,
               edgecolor=SIGNAL, linewidth=1.5, label="Above limit (not with Laney limits)")
    sx = sx + wx
    base_end = months.index(BASELINE[1])
    ax.axvspan(-0.5, base_end + 0.5, color=GRID, alpha=0.5, lw=0)
    ax.text(base_end / 2, 1.01, "baseline 2020–2022", ha="center", va="bottom",
            color=MUTED, fontsize=9, transform=ax.get_xaxis_transform())
    ax.set_xlim(-1, idx[-1] + 8)
    ax.text(idx[-1] + 1, p_bar, f"center {p_bar:.1%}", va="center", color=MUTED, fontsize=9)
    ticks = [i for i, m in enumerate(months) if m.endswith("-01")]
    ax.set_xticks(ticks, [months[i][:4] for i in ticks])
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_ylabel("Share of monthly reports", color=MUTED)
    ax.set_title(f"{problem}: monthly share of {noun} (p-chart, 3σ limits)", loc="left",
                 color=INK, fontsize=12, pad=18)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED)
    ax.grid(axis="y", color=GRID, lw=0.6)
    if sx:
        ax.legend(frameon=False, loc="upper right", labelcolor=INK)
    fig.text(0.01, 0.01, footnote, color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    name = problem.lower().replace(" ", "_").replace("/", "_")
    fig.savefig(out_dir / f"{name}.png", dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--by", choices=["fda_terms", "predicted"], default="fda_terms")
    args = ap.parse_args()
    conn = sqlite3.connect(DB_PATH)
    if args.by == "fda_terms":
        out_dir, last, items = OUT_DIR, LAST_MONTH, PROBLEMS
        noun = "DQA reports"
        footnote = ("Source: openFDA MAUDE, product code DQA. Counts of reports, not failure rates. "
                    "FDA problem terms.")
        totals_sql = "SELECT month, COUNT(*) FROM report_features GROUP BY month"
        count_sql = ("SELECT f.month, COUNT(*) FROM report_problems p JOIN report_features f "
                     "USING (mdr_report_key) WHERE p.problem = ? GROUP BY f.month")
    else:
        out_dir, last, items = OUT_DIR_PREDICTED, LAST_MONTH_PREDICTED, PREDICTED
        noun = "described reports"
        footnote = ("Source: openFDA MAUDE, DQA. Category predicted by keyword rules (macro-F1 0.60 on "
                    "labeled test set); see docs/model_card.md. Reports, not failure rates.")
        totals_sql = ("SELECT f.month, COUNT(*) FROM report_predictions p JOIN report_features f "
                      "USING (mdr_report_key) GROUP BY f.month")
        count_sql = ("SELECT f.month, COUNT(*) FROM report_predictions p JOIN report_features f "
                     "USING (mdr_report_key) WHERE p.predicted_label = ? GROUP BY f.month")
    out_dir.mkdir(parents=True, exist_ok=True)
    months = months_between(BASELINE[0], last)
    totals = dict(conn.execute(totals_sql))
    n = [totals.get(m, 0) for m in months]
    rows = []
    for item in items:
        counts = dict(conn.execute(count_sql, (item,)))
        x = [counts.get(m, 0) for m in months]
        p_bar, sd, sigma_z = analyze(months, n, x)
        signals = find_signals(months, n, x, p_bar, sd, sigma_z)
        plot(item, months, n, x, p_bar, sd, signals, out_dir, footnote, noun)
        print(f"{item:<25} center {p_bar:6.1%}  sigma_z {sigma_z:4.2f}  signals {len(signals)}")
        rows += [(item, round(p_bar, 4), round(sigma_z, 2), *s) for s in signals]
        if not signals:
            rows.append((item, round(p_bar, 4), round(sigma_z, 2), "", "none", "", ""))
    with (out_dir / "signals.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category_or_term", "baseline_share", "sigma_z", "month", "rule", "share", "survives_laney"])
        w.writerows(rows)
    print(f"Saved charts and signals.csv to {out_dir.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

"""Independent cross-check of the SQL results with pandas.

Each check recomputes a query result from the RAW tables (reports, narratives),
without using the analysis tables built by src/build_tables.py, and compares it
with the CSV written by src/run_queries.py. If two independent methods agree,
an error in one of them is much less likely.

Run from the project root:  python tests/check_queries.py
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results" / "queries"
conn = sqlite3.connect(ROOT / "data" / "maude.db")
reports = pd.read_sql("SELECT * FROM reports", conn)
reports["year"] = reports["date_received"].str[:4].astype(int)
problems = (
    reports[["mdr_report_key", "year", "event_type", "product_problems"]]
    .assign(problem=lambda d: d["product_problems"].str.split("; "))
    .explode("problem")
    .query("problem != '' and problem.notna()", engine="python")
)
failures = []


def check(name, condition):
    print(("PASS " if condition else "FAIL ") + name)
    if not condition:
        failures.append(name)


def load(stem):
    return pd.read_csv(RESULTS / f"{stem}.csv")


# Q1: reports per year
q1 = load("01_reports_per_year").set_index("year")["n_reports"]
check("Q1 reports per year", q1.equals(reports.groupby("year").size().rename("n_reports")))
check("Q1 total equals number of reports", q1.sum() == len(reports))

# Q2: event types per year
q2 = load("02_event_type_per_year").set_index("year")
mal = reports[reports.event_type == "Malfunction"].groupby("year").size()
check("Q2 malfunction per year", q2["malfunction"].equals(mal.reindex(q2.index, fill_value=0).rename("malfunction")))
check("Q2 columns add up to total", (q2[["malfunction", "injury", "death", "other_or_missing"]].sum(axis=1) == q2["total"]).all())

# Q4: top problems
q4 = load("04_top_problems").set_index("problem")["n_reports"]
pd_top = problems.groupby("problem").size().sort_values(ascending=False).head(15)
check("Q4 top 15 problems and counts", q4.to_dict() == pd_top.to_dict())

# Q6: change in share 2020-2022 vs 2023-2025
q6 = load("06_fastest_growing_problems").set_index("problem")
n_before = (reports.year.between(2020, 2022)).sum()
n_after = (reports.year.between(2023, 2025)).sum()
for prob in q6.index[:5]:
    k_b = ((problems.problem == prob) & problems.year.between(2020, 2022)).sum()
    k_a = ((problems.problem == prob) & problems.year.between(2023, 2025)).sum()
    change = round(100 * k_a / n_after - 100 * k_b / n_before, 1)
    check(f"Q6 change for '{prob}'", abs(change - q6.loc[prob, "change_pp"]) < 0.051)

# Q7: manufacturer groups cover every report
q7_all = pd.read_sql("SELECT COUNT(*) AS n FROM report_features", conn)["n"][0]
check("Q7 report_features has one row per report", q7_all == len(reports))

# Q9: harm reports
q9 = load("09_problems_in_death_injury").set_index("problem")
harm = problems[problems.event_type.isin(["Death", "Injury"])].groupby("problem").size()
top = q9.index[0]
check(f"Q9 harm count for '{top}'", q9.loc[top, "total_harm_reports"] == harm[top])

# Q10: missing descriptions recomputed from narratives
narr = pd.read_sql(
    "SELECT DISTINCT mdr_report_key FROM narratives "
    "WHERE text_type_code = 'Description of Event or Problem' AND text IS NOT NULL AND TRIM(text) != ''",
    conn,
)
missing = (~reports.mdr_report_key.isin(narr.mdr_report_key)).groupby(reports.year).sum()
q10 = load("10_narrative_completeness").set_index("year")["missing_description"]
check("Q10 missing descriptions per year", (q10 == missing.reindex(q10.index)).all())

print(f"\n{len(failures)} failure(s)")
sys.exit(1 if failures else 0)

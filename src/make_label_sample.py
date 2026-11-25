"""Draw the stratified sample of report descriptions to label by hand.

Run from the project root, after src/build_tables.py:  python src/make_label_sample.py
Output: labels/sample_to_label.csv (opens in Excel; fill the empty columns).

Design (see docs/labeling_guide.md):
- Only reports with a description (the classifier works on text).
- Exact duplicate texts are removed first (after upper-casing and collapsing spaces),
  so template narratives are not labeled many times.
- Stratified by period, so the later date-based split has enough recent reports:
  60 before 2014, 120 in 2014-2019, 120 in 2020 or later.
- Manufacturer and FDA problem codes are NOT shown, so they cannot bias the labels.
  They stay in the database and are joined later by mdr_report_key.
- Fixed random seed: the same database always gives the same sample.
- The script refuses to overwrite an existing sample, to protect labels already made.
"""

import csv
import random
import re
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "maude.db"
OUT_PATH = PROJECT_ROOT / "labels" / "sample_to_label.csv"
SEED = 42
STRATA = [("before_2014", None, 2013, 60), ("2014_2019", 2014, 2019, 120), ("2020_plus", 2020, None, 120)]


def normalize(text):
    return re.sub(r"\s+", " ", text.upper()).strip()


def main():
    if OUT_PATH.exists():
        sys.exit(f"{OUT_PATH} already exists. Delete or rename it on purpose before drawing a new sample.")
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT f.mdr_report_key, r.date_received, f.year, f.description "
        "FROM report_features f JOIN reports r USING (mdr_report_key) "
        "WHERE f.description IS NOT NULL "
        "ORDER BY r.date_received, f.mdr_report_key"
    ).fetchall()

    # Keep the first (earliest) report of each distinct text.
    seen, unique = set(), []
    for row in rows:
        norm = normalize(row[3])
        if norm not in seen:
            seen.add(norm)
            unique.append(row)
    print(f"Reports with description: {len(rows)}; distinct texts: {len(unique)}")

    rng = random.Random(SEED)
    sample = []
    for name, start, end, size in STRATA:
        pool = [r for r in unique if (start is None or r[2] >= start) and (end is None or r[2] <= end)]
        chosen = rng.sample(pool, size)
        print(f"  {name:<12} pool {len(pool):>5} -> {size}")
        sample += [(name, *r) for r in chosen]
    rng.shuffle(sample)  # mixed order, so labeling is not done period by period

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: Excel reads it correctly
        writer = csv.writer(f)
        writer.writerow(["label_id", "mdr_report_key", "date_received", "stratum", "description",
                         "label", "secondary_label", "confidence", "notes"])
        for i, (stratum, key, date, year, desc) in enumerate(sample, start=1):
            writer.writerow([i, key, date, stratum, desc, "", "", "", ""])
    print(f"Saved {len(sample)} rows to {OUT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

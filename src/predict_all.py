"""Assign a predicted failure category to every report that has an event description.

Run from the project root, after src/build_tables.py:  python src/predict_all.py
Creates (or rebuilds) the table `report_predictions` in data/maude.db and writes
results/classification/predicted_vs_true.csv.

Model: the keyword rules of src/classify.py. They were chosen because they had the
best macro-F1 on the date-split test set (docs/model_card.md) and were fixed before
any label existed. Reports without a description get no prediction.

Calibration check: on the 120 labeled test reports (2020+), the number of reports the
model PREDICTS per category is compared with the number the author LABELED. If a
category is over- or under-predicted, its level in the trend charts is biased in the
same direction; changes over time are still informative if that bias is stable.
"""

import csv
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify import CATEGORIES, DEFAULT_LABELS, TEST_FROM_YEAR, clean, keyword_predict, load_labels  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "maude.db"
OUT = PROJECT_ROOT / "results" / "classification" / "predicted_vs_true.csv"


def main():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT mdr_report_key, description FROM report_features WHERE description IS NOT NULL"
    ).fetchall()
    preds = keyword_predict([clean(d) for _, d in rows])
    conn.executescript(
        """
        DROP TABLE IF EXISTS report_predictions;
        CREATE TABLE report_predictions (
            mdr_report_key  TEXT PRIMARY KEY,
            predicted_label TEXT,
            method          TEXT);
        """
    )
    conn.executemany(
        "INSERT INTO report_predictions VALUES (?,?,?)",
        [(key, p, "keywords_v1") for (key, _), p in zip(rows, preds)],
    )
    conn.commit()
    print(f"Predicted {len(rows)} reports with a description.")
    for label, n in Counter(preds).most_common():
        print(f"  {label:<20} {n:>6}  ({n / len(rows):.1%})")

    # Calibration check on the labeled test reports.
    if Path(DEFAULT_LABELS).exists():
        test = [r for r in load_labels(DEFAULT_LABELS) if r["year"] >= TEST_FROM_YEAR]
        true_counts = Counter(r["label"] for r in test)
        pred_counts = Counter(keyword_predict([r["text"] for r in test]))
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["category", "labeled_test_reports", "predicted_test_reports", "predicted_minus_labeled"])
            for c in CATEGORIES:
                w.writerow([c, true_counts[c], pred_counts[c], pred_counts[c] - true_counts[c]])
        print(f"\nCalibration on {len(test)} labeled test reports saved to {OUT.relative_to(PROJECT_ROOT)}")
    conn.close()


if __name__ == "__main__":
    main()

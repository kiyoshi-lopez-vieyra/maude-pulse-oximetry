"""Run every query in sql/ and save each result as a CSV in results/queries/.

Run from the project root, after src/build_tables.py:  python src/run_queries.py
"""

import csv
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "maude.db"
SQL_DIR = PROJECT_ROOT / "sql"
OUT_DIR = PROJECT_ROOT / "results" / "queries"


def main():
    if not DB_PATH.exists():
        sys.exit("data/maude.db not found. Run src/download.py and src/build_tables.py first.")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    for sql_file in sorted(SQL_DIR.glob("*.sql")):
        cursor = conn.execute(sql_file.read_text(encoding="utf-8"))
        header = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        out_file = OUT_DIR / (sql_file.stem + ".csv")
        with out_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        print(f"{sql_file.name:<40} {len(rows):>4} rows -> {out_file.relative_to(PROJECT_ROOT)}")
    conn.close()


if __name__ == "__main__":
    main()

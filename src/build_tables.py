"""Build analysis-ready tables from the raw download.

Run from the project root, after src/download.py:  python src/build_tables.py

Creates (or rebuilds) three tables in data/maude.db:
- report_problems: one row per (report, FDA product problem). The raw table stores
  problems as a '; '-joined string, which is hard to count with SQL.
- report_features: one row per report with year, month, a normalized manufacturer
  group, and the event description text (all 'Description of Event or Problem'
  texts of the report joined together).
- manufacturer_map: every raw manufacturer name, the group it was mapped to,
  and HOW it was mapped, so every decision can be audited.

Manufacturer normalization rules (documented in docs/data_dictionary.md):
1. By the device manufacturer name (e.g. any name containing "MASIMO" -> Masimo).
2. If the name is only a factory/site (e.g. "GALWAY", "SANMINA-SCI SYSTEMS"),
   use the brand name as evidence (e.g. brand "NELLCOR OXIMAX N-65" -> Covidien/Nellcor).
   These rows are marked method = 'brand' so they can be excluded in a sensitivity check.
3. Otherwise keep the raw name as its own group (method = 'raw').
"""

import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "maude.db"

# (substring in the manufacturer name, group). First match wins.
NAME_RULES = [
    ("MASIMO", "Masimo"),
    ("MASSIMO", "Masimo"),          # misspelling seen in the data
    ("NELLCOR", "Covidien/Nellcor"),
    ("COVIDIEN", "Covidien/Nellcor"),
    ("TYCO", "Covidien/Nellcor"),
    ("PHILIPS", "Philips"),
    ("INVIVO", "Philips"),          # data shows "INVIVO, A DIVISION OF PHILIPS ..."
    ("MEDIANA", "Mediana"),
    ("CAREFUSION", "CareFusion"),
    ("NONIN", "Nonin"),
    ("SMITHS MEDICAL", "Smiths Medical"),
    ("MEDLINE", "Medline"),
    ("GE HEALTHCARE", "GE Healthcare"),
    ("EDWARDS", "Edwards Lifesciences"),
    ("WELCH ALLYN", "Welch Allyn"),
]

# Used only when the name gives no group. (substring in the brand name, group).
BRAND_RULES = [
    ("NELLCOR", "Covidien/Nellcor"),
    ("OXIMAX", "Covidien/Nellcor"),
    ("MASIMO", "Masimo"),
    ("BCI", "Smiths Medical"),      # narratives mention "SMITHS MEDICAL BCI"
]

UNKNOWN_NAMES = {"", "*", "UNK", "UNKNOWN", "NULL", "NI", "NA"}


def map_manufacturer(name, brand):
    """Return (group, method)."""
    n = (name or "").upper().strip()
    b = (brand or "").upper().strip()
    for sub, group in NAME_RULES:
        if sub in n:
            return group, "name"
    for sub, group in BRAND_RULES:
        if sub in b:
            return group, "brand"
    if n in UNKNOWN_NAMES:
        return "Unknown", "unknown"
    return n.title(), "raw"


def main():
    if not DB_PATH.exists():
        sys.exit("data/maude.db not found. Run src/download.py first.")
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        DROP TABLE IF EXISTS report_problems;
        DROP TABLE IF EXISTS report_features;
        DROP TABLE IF EXISTS manufacturer_map;
        CREATE TABLE report_problems (
            mdr_report_key TEXT, problem TEXT,
            PRIMARY KEY (mdr_report_key, problem));
        CREATE TABLE report_features (
            mdr_report_key     TEXT PRIMARY KEY,
            year               INTEGER,
            month              TEXT,     -- YYYY-MM of date_received
            manufacturer_group TEXT,
            mfr_group_method   TEXT,     -- name | brand | raw | unknown
            description        TEXT,     -- all event descriptions, joined
            description_chars  INTEGER);
        CREATE TABLE manufacturer_map (
            raw_name TEXT, brand_name TEXT, manufacturer_group TEXT,
            method TEXT, n_reports INTEGER);
        """
    )

    rows = conn.execute(
        "SELECT mdr_report_key, date_received, manufacturer_name, brand_name, product_problems "
        "FROM reports"
    ).fetchall()

    descriptions = {}
    for key, text in conn.execute(
        "SELECT mdr_report_key, text FROM narratives "
        "WHERE text_type_code = 'Description of Event or Problem' "
        "ORDER BY mdr_report_key, rowid"
    ):
        # Some reports repeat the same description block (e.g. initial report and
        # follow-up). Keep each distinct text once, in its original order.
        if text and text.strip() not in descriptions.setdefault(key, []):
            descriptions[key].append(text.strip())

    map_counts = {}
    for key, date, mfr, brand, problems in rows:
        for p in (problems or "").split("; "):
            if p:
                conn.execute("INSERT OR IGNORE INTO report_problems VALUES (?,?)", (key, p))
        group, method = map_manufacturer(mfr, brand)
        map_key = ((mfr or "").strip(), (brand or "").strip(), group, method)
        map_counts[map_key] = map_counts.get(map_key, 0) + 1
        desc = " ".join(descriptions.get(key, [])) or None
        conn.execute(
            "INSERT INTO report_features VALUES (?,?,?,?,?,?,?)",
            (
                key,
                int(date[:4]) if date else None,
                date[:7] if date else None,
                group,
                method,
                desc,
                len(desc) if desc else 0,
            ),
        )
    conn.executemany(
        "INSERT INTO manufacturer_map VALUES (?,?,?,?,?)",
        [(*k, n) for k, n in map_counts.items()],
    )
    conn.commit()

    # Self-checks: every report must appear exactly once in report_features.
    n_reports = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    n_features = conn.execute("SELECT COUNT(*) FROM report_features").fetchone()[0]
    assert n_reports == n_features, "report_features does not match reports"
    n_mapped = conn.execute("SELECT SUM(n_reports) FROM manufacturer_map").fetchone()[0]
    assert n_mapped == n_reports, "manufacturer_map does not cover every report"

    print(f"report_features: {n_features} rows")
    print("report_problems:", conn.execute("SELECT COUNT(*) FROM report_problems").fetchone()[0], "rows")
    print("\nManufacturer groups by method:")
    for row in conn.execute(
        "SELECT mfr_group_method, COUNT(*) FROM report_features GROUP BY 1 ORDER BY 2 DESC"
    ):
        print(f"  {row[0]:<8} {row[1]}")
    conn.close()


if __name__ == "__main__":
    main()

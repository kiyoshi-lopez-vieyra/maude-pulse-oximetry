"""Download all MAUDE reports for one FDA product code into a SQLite database.

Run from the project root:  python src/download.py
Output: data/maude.db (ignored by Git; anyone can rebuild it with this script).

Design choices (see docs/scope.md):
- The device family is defined by product code (DQA = pulse oximeter), not by keyword.
- The full raw JSON of every report is kept, so nothing is lost if we need a field later.
- mdr_report_key is the primary key, so re-running the script never creates duplicates.
"""

import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

PRODUCT_CODE = "DQA"
BASE_URL = "https://api.fda.gov/device/event.json"
PAGE_SIZE = 1000        # openFDA maximum for `limit`
MAX_SKIP = 25000        # openFDA maximum for `skip`
PAUSE_SECONDS = 0.5     # stay well below the 240 requests/minute limit

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "maude.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    mdr_report_key     TEXT PRIMARY KEY,
    report_number      TEXT,
    date_received      TEXT,   -- ISO format YYYY-MM-DD
    date_of_event      TEXT,   -- ISO format, often missing
    event_type         TEXT,   -- e.g. Malfunction, Injury, Death
    report_source_code TEXT,
    product_code       TEXT,
    generic_name       TEXT,
    brand_name         TEXT,
    manufacturer_name  TEXT,
    model_number       TEXT,
    product_problems   TEXT,   -- unique values joined with '; '
    raw_json           TEXT    -- the complete original record
);
CREATE TABLE IF NOT EXISTS narratives (
    mdr_report_key TEXT,
    text_type_code TEXT,       -- e.g. 'Description of Event or Problem'
    text           TEXT,
    FOREIGN KEY (mdr_report_key) REFERENCES reports (mdr_report_key)
);
CREATE TABLE IF NOT EXISTS download_log (
    run_at_utc     TEXT,
    query          TEXT,
    total_in_api   INTEGER,
    rows_in_db     INTEGER
);
"""


def get_api_key() -> str:
    load_dotenv(PROJECT_ROOT / ".env")
    key = os.getenv("OPENFDA_API_KEY", "").strip()
    if not key or key == "your_key_here":
        sys.exit("No API key found. Create a .env file (see .env.example).")
    return key


def iso_date(value):
    """'20200427' -> '2020-04-27'. Returns None if missing or malformed."""
    if not value or len(value) != 8 or not value.isdigit():
        return None
    return f"{value[:4]}-{value[4:6]}-{value[6:]}"


def pick_device(record):
    """A report can list several devices; use the one with our product code."""
    devices = record.get("device") or [{}]
    for device in devices:
        if device.get("device_report_product_code") == PRODUCT_CODE:
            return device
    return devices[0]


def fetch_page(key, search, skip):
    params = {
        "api_key": key,
        "search": search,
        "sort": "date_received:asc",
        "limit": PAGE_SIZE,
        "skip": skip,
    }
    for attempt in range(3):
        response = requests.get(BASE_URL, params=params, timeout=60)
        if response.status_code == 200:
            return response.json()
        # Print the error WITHOUT the URL, so the key never appears on screen.
        print(f"  HTTP {response.status_code} at skip={skip}, attempt {attempt + 1}")
        time.sleep(5)
    sys.exit("Download stopped after 3 failed attempts. Nothing was lost; run it again.")


def save_page(conn, records):
    for r in records:
        key = r.get("mdr_report_key")
        if not key:
            continue
        device = pick_device(r)
        # Some reports have empty (None) entries in product_problems; drop them.
        problems = "; ".join(sorted({p for p in (r.get("product_problems") or []) if p}))
        conn.execute(
            "INSERT OR REPLACE INTO reports VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                key,
                r.get("report_number"),
                iso_date(r.get("date_received")),
                iso_date(r.get("date_of_event")),
                r.get("event_type"),
                r.get("report_source_code"),
                device.get("device_report_product_code"),
                device.get("generic_name"),
                device.get("brand_name"),
                device.get("manufacturer_d_name"),
                device.get("model_number"),
                problems,
                json.dumps(r),
            ),
        )
        # Replace this report's narratives so re-runs don't duplicate them.
        conn.execute("DELETE FROM narratives WHERE mdr_report_key = ?", (key,))
        for t in r.get("mdr_text") or []:
            conn.execute(
                "INSERT INTO narratives VALUES (?,?,?)",
                (key, t.get("text_type_code"), t.get("text")),
            )
    conn.commit()


def main():
    key = get_api_key()
    search = f"device.device_report_product_code:{PRODUCT_CODE}"
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    first = fetch_page(key, search, 0)
    total = first["meta"]["results"]["total"]
    print(f"Query: {search}")
    print(f"Reports in the API: {total}")
    if total > MAX_SKIP + PAGE_SIZE:
        sys.exit("Too many reports for skip-based paging. We need search_after; tell Claude.")

    save_page(conn, first["results"])
    skip = PAGE_SIZE
    while skip < total:
        print(f"  downloading {skip} to {min(skip + PAGE_SIZE, total)}...")
        time.sleep(PAUSE_SECONDS)
        page = fetch_page(key, search, skip)
        save_page(conn, page.get("results", []))
        skip += PAGE_SIZE

    rows = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    n_texts = conn.execute("SELECT COUNT(*) FROM narratives").fetchone()[0]
    conn.execute(
        "INSERT INTO download_log VALUES (?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(timespec="seconds"), search, total, rows),
    )
    conn.commit()
    conn.close()

    print(f"\nReports in the API:      {total}")
    print(f"Unique reports saved:    {rows}")
    print(f"Narrative texts saved:   {n_texts}")
    if rows != total:
        print("NOTE: the counts differ. We will investigate before analyzing.")
    print(f"Database: {DB_PATH}")


if __name__ == "__main__":
    main()

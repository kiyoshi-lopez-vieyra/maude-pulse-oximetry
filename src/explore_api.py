"""First contact with the openFDA device adverse event API.

Goals (nothing is assumed, everything is checked against the real API):
  1. Confirm the API key works.
  2. Save ONE raw report so we can see the real field names.
  3. Count reports that mention "oximeter" by FDA product code,
     to decide which product code(s) define our device family.

Run from the project root:  python src/explore_api.py
"""

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_URL = "https://api.fda.gov/device/event.json"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

# Search term for the first exploration. The field name is an assumption
# that this script verifies: if it returns 0 results we will adjust it.
SEARCH = 'device.generic_name:"oximeter"'


def get_api_key() -> str:
    load_dotenv(PROJECT_ROOT / ".env")
    key = os.getenv("OPENFDA_API_KEY", "").strip()
    if not key or key == "your_key_here":
        sys.exit("No API key found. Create a .env file (see .env.example).")
    return key


def query(params: dict) -> dict:
    """Send one request. Errors are printed WITHOUT the URL, so the key never shows up."""
    response = requests.get(BASE_URL, params=params, timeout=30)
    if response.status_code != 200:
        try:
            detail = response.json().get("error", {})
        except ValueError:
            detail = response.text[:200]
        print(f"Request failed. HTTP {response.status_code}: {detail}")
        return {}
    return response.json()


def main() -> None:
    key = get_api_key()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 1 and 2: one sample report
    print(f"Search: {SEARCH}\n")
    data = query({"api_key": key, "search": SEARCH, "limit": 1})
    if not data:
        return

    total = data["meta"]["results"]["total"]
    print(f"Total matching reports: {total}")

    record = data["results"][0]
    sample_path = RAW_DIR / "sample_report.json"
    sample_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"Saved one raw report to: {sample_path}\n")

    print("Top-level fields:", sorted(record.keys()))
    if record.get("device"):
        print("Fields inside device[0]:", sorted(record["device"][0].keys()))
    if record.get("mdr_text"):
        print("Fields inside mdr_text[0]:", sorted(record["mdr_text"][0].keys()))

    # 3: how many reports per product code?
    print("\nReports by product code (top 10):")
    counts = query({
        "api_key": key,
        "search": SEARCH,
        "count": "device.device_report_product_code.exact",
    })
    for row in counts.get("results", [])[:10]:
        print(f"  {row['term']:>6}  {row['count']}")


if __name__ == "__main__":
    main()

"""Label consistency re-test: re-label 30 random reports blind, then measure agreement.

Step 1 (once):   python src/consistency.py --create
                 -> labels/relabel_30.xlsx with 30 random descriptions and empty drop-downs.
                 Label them at least one week after the original labels, without looking at them.
Step 2:          python src/consistency.py
                 -> agreement and Cohen's kappa against the final labels (and the pre-audit ones),
                    saved to results/classification/consistency.json.

Cohen's kappa corrects raw agreement for the agreement expected by chance:
1 = perfect, 0 = no better than chance. Rough reading: above 0.8 very good, 0.6-0.8 good.
"""

import argparse
import json
import random
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from sklearn.metrics import cohen_kappa_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify import read_xlsx  # noqa: E402
from make_label_workbook import ORDER  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "labels" / "sample_to_label.xlsx"
PRE_AUDIT = ROOT / "labels" / "sample_to_label_v1_before_audit.xlsx"
RELABEL = ROOT / "labels" / "relabel_30.xlsx"
OUT = ROOT / "results" / "classification" / "consistency.json"
SEED = 2026
N = 30


def create():
    if RELABEL.exists():
        sys.exit(f"{RELABEL} already exists; it may contain labels. Rename it on purpose first.")
    rows = read_xlsx(FINAL)
    chosen = sorted(random.Random(SEED).sample(rows, N), key=lambda r: random.Random(r["label_id"]).random())
    wb = Workbook()
    ws = wb.active
    ws.title = "relabel"
    ws.append(["label_id", "description", "label"])
    for r in chosen:
        ws.append([int(r["label_id"]), r["description"], None])
    ws.column_dimensions["A"].width = 9
    ws.column_dimensions["B"].width = 110
    ws.column_dimensions["C"].width = 22
    for cell in ws[1]:
        cell.font = Font(name="Arial", bold=True)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="Arial", size=10)
            cell.alignment = Alignment(vertical="top", wrap_text=cell.column_letter == "B")
        row[2].fill = PatternFill("solid", fgColor="FFF2CC")
    dv = DataValidation(type="list", formula1='"' + ",".join(ORDER) + '"', allow_blank=True, showErrorMessage=True)
    ws.add_data_validation(dv)
    dv.add(f"C2:C{N + 1}")
    ws.freeze_panes = "C2"
    wb.save(RELABEL)
    print(f"Created {RELABEL.relative_to(ROOT)} with {N} reports. Do not open sample_to_label.xlsx while labeling.")


def measure():
    sheet = read_xlsx_sheet(RELABEL, "relabel")
    redo = {r["label_id"]: r["label"].strip() for r in sheet if r["label"].strip()}
    if len(redo) < N:
        sys.exit(f"Only {len(redo)} of {N} reports re-labeled. Finish all of them first.")
    result = {"n": len(redo)}
    for name, path in (("final_labels", FINAL), ("pre_audit_labels", PRE_AUDIT)):
        if not path.exists():
            continue
        first = {r["label_id"]: r["label"] for r in read_xlsx(path)}
        ids = sorted(redo, key=int)
        a, b = [first[i] for i in ids], [redo[i] for i in ids]
        result[name] = {
            "agreement": round(sum(x == y for x, y in zip(a, b)) / len(ids), 3),
            "cohen_kappa": round(float(cohen_kappa_score(a, b)), 3),
            "disagreements": [{"label_id": i, "first": x, "second": y} for i, x, y in zip(ids, a, b) if x != y],
        }
        print(f"{name}: agreement {result[name]['agreement']:.0%}, Cohen's kappa {result[name]['cohen_kappa']:.2f}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Saved {OUT.relative_to(ROOT)}")


def read_xlsx_sheet(path, sheet):
    from openpyxl import load_workbook
    ws = load_workbook(path, read_only=True, data_only=True)[sheet]
    rows = list(ws.iter_rows(values_only=True))
    header = [str(h) for h in rows[0]]
    return [{h: ("" if v is None else str(v)) for h, v in zip(header, r)} for r in rows[1:] if any(r)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--create", action="store_true")
    args = ap.parse_args()
    create() if args.create else measure()

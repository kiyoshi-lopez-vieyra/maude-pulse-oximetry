"""Convert the labeling CSV into an Excel workbook with drop-down lists.

Run from the project root:  python src/make_label_workbook.py
Input:  labels/sample_to_label.csv (labels already made are kept)
Output: labels/sample_to_label.xlsx

Drop-downs for `label`, `secondary_label` and `confidence` prevent typos.
Categories are ordered by how often they were used in the first 50 labels,
then the unused ones. Excel also rejects any value that is not in the list.
The script refuses to overwrite an existing workbook, to protect labels made in it.
"""

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify import CATEGORIES, read_csv_any  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "labels" / "sample_to_label.csv"
XLSX_PATH = PROJECT_ROOT / "labels" / "sample_to_label.xlsx"
ORDER = ["accuracy", "alarm", "display", "signal_acquisition", "physical_damage",
         "power_battery", "software_behavior", "patient_contact", "other", "unclear"]
HEADERS = ["label_id", "mdr_report_key", "date_received", "stratum", "description",
           "label", "secondary_label", "confidence", "notes"]
FONT = "Arial"
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")
HEADER_FILL = PatternFill("solid", fgColor="D9E1F2")


def main(original_dates=None):
    assert sorted(ORDER) == sorted(CATEGORIES), "ORDER must contain every category once"
    if XLSX_PATH.exists():
        sys.exit(f"{XLSX_PATH} already exists. Rename it on purpose before creating a new one.")
    rows = read_csv_any(CSV_PATH)
    original_dates = original_dates or {}

    wb = Workbook()
    ws = wb.active
    ws.title = "labels"
    ws.append(HEADERS)
    for r in rows:
        label = r["label"].strip().lower()
        secondary = r["secondary_label"].strip().lower()
        conf = r["confidence"].strip()
        ws.append([
            int(r["label_id"]),
            r["mdr_report_key"].strip(),
            original_dates.get(r["mdr_report_key"].strip(), r["date_received"]),
            r["stratum"],
            r["description"],
            label or None,
            secondary or None,
            int(conf) if conf in ("1", "2", "3") else None,
            r["notes"].strip() or None,
        ])

    widths = {"A": 9, "B": 17, "C": 15, "D": 12, "E": 95, "F": 21, "G": 21, "H": 12, "I": 45}
    for col, width in widths.items():
        ws.column_dimensions[col].width = width
    for cell in ws[1]:
        cell.font = Font(name=FONT, bold=True)
        cell.fill = HEADER_FILL
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name=FONT, size=10)
            cell.alignment = Alignment(vertical="top", wrap_text=cell.column_letter in ("E", "I"))
        for cell in row[5:9]:
            cell.fill = INPUT_FILL
        row[1].number_format = "@"   # keep report keys as text
        row[2].number_format = "@"   # keep dates as YYYY-MM-DD text
    ws.freeze_panes = "F2"
    ws.auto_filter.ref = f"A1:I{ws.max_row}"

    last = ws.max_row
    cat_list = '"' + ",".join(ORDER) + '"'
    for col in ("F", "G"):
        dv = DataValidation(type="list", formula1=cat_list, allow_blank=True)
        dv.error = "Elige una categoría de la lista."
        dv.errorTitle = "Categoría no válida"
        dv.showErrorMessage = True
        ws.add_data_validation(dv)
        dv.add(f"{col}2:{col}{last}")
    conf_dv = DataValidation(type="list", formula1='"3,2,1"', allow_blank=True)
    conf_dv.error = "Usa 3 (seguro), 2 (bastante seguro) o 1 (adivinando)."
    conf_dv.errorTitle = "Confianza no válida"
    conf_dv.showErrorMessage = True
    ws.add_data_validation(conf_dv)
    conf_dv.add(f"H2:H{last}")

    guide = wb.create_sheet("guia")
    lines = [
        ("Cómo usar esta hoja", True),
        ("Llena solo las columnas amarillas de la hoja 'labels': label, secondary_label, confidence y notes.", False),
        ("label y secondary_label: elige de la lista desplegable (flecha a la derecha de la celda).", False),
        ("confidence: 3 = seguro, 2 = bastante seguro, 1 = adivinando.", False),
        ("notes: solo dudas o razones de casos difíciles. Déjala vacía si la etiqueta es clara.", False),
        ("Guarda con Ctrl+S (formato .xlsx). Ya no uses el archivo .csv.", False),
        ("", False),
        ("Categorías (pregunta: ¿qué observó quien reportó?)", True),
        ("accuracy: hay un número, pero está mal (incluye valores con el sensor desconectado).", False),
        ("alarm: la alarma sonora o visual no funciona bien, o hay falsas alarmas.", False),
        ("display: la pantalla falla (segmentos faltantes, en blanco, artefactos).", False),
        ("signal_acquisition: no logra leer, o la lectura aparece y desaparece.", False),
        ("physical_damage: daño físico observado en equipo, sensor o cable.", False),
        ("power_battery: batería, carga, se apaga solo, no enciende.", False),
        ("software_behavior: reinicios, congelamiento, mensajes o códigos de error sin otra causa.", False),
        ("patient_contact: daño por contacto físico (quemadura, piel, descarga).", False),
        ("other: problema claro que no cabe en ninguna categoría.", False),
        ("unclear: no hay información suficiente para decidir.", False),
        ("", False),
        ("Guía completa: docs/labeling_guide.md", False),
    ]
    for i, (text, bold) in enumerate(lines, start=1):
        cell = guide.cell(row=i, column=1, value=text)
        cell.font = Font(name=FONT, bold=bold, size=11 if bold else 10)
    guide.column_dimensions["A"].width = 110

    XLSX_PATH.parent.mkdir(parents=True, exist_ok=True)
    wb.save(XLSX_PATH)
    labeled = sum(1 for r in rows if r["label"].strip())
    for r in rows:
        for field in ("label", "secondary_label"):
            value = r[field].strip().lower()
            if value and value not in CATEGORIES:
                print(f"CHECK row {r['label_id']}: {field} '{value}' is not a valid category")
        if r["label"].strip() and r["confidence"].strip() not in ("1", "2", "3"):
            print(f"CHECK row {r['label_id']}: confidence is missing or invalid")
    print(f"Saved {XLSX_PATH.relative_to(PROJECT_ROOT)} with {len(rows)} rows ({labeled} already labeled).")


if __name__ == "__main__":
    import sqlite3
    db = PROJECT_ROOT / "data" / "maude.db"
    dates = dict(sqlite3.connect(db).execute("SELECT mdr_report_key, date_received FROM reports")) if db.exists() else {}
    main(dates)

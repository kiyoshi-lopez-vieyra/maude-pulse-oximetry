# Data dictionary

Database: `data/maude.db` (SQLite). Built by `src/download.py` (raw tables), `src/build_tables.py` (analysis tables) and `src/predict_all.py` (predicted categories).
Snapshot described here: downloaded 2026-11-24, product code DQA, **14,234 reports**, `date_received` from 1991-12-31 to 2026-10-30.

## Raw tables (`src/download.py`)

### `reports` (one row per MAUDE report)
| Column | Type | Source field (openFDA) | Notes |
|---|---|---|---|
| mdr_report_key | TEXT, PK | `mdr_report_key` | Unique per report. Follow-ups are inside the same record (`type_of_report`), so they do **not** create extra rows. |
| report_number | TEXT | `report_number` | Also unique in this snapshot (14,234 distinct). |
| date_received | TEXT (YYYY-MM-DD) | `date_received` | Date FDA received the report. Never missing. Used for all time analyses. |
| date_of_event | TEXT (YYYY-MM-DD) | `date_of_event` | Missing in 2,255 reports (15.8%). Not used for trends. |
| event_type | TEXT | `event_type` | Malfunction 13,044; Injury 591; Death 365; Other 168; empty 66. |
| report_source_code | TEXT | `report_source_code` | Manufacturer 13,518; User facility 414; Voluntary 295; Distributor 7. |
| product_code | TEXT | `device[].device_report_product_code` | Always DQA (the device with code DQA is chosen when a report lists several devices). |
| generic_name | TEXT | `device[].generic_name` | Free text, inconsistent (e.g. "OXIMETER", "PULSE OXIMETER", "BATTERY", "PUMP, INFUSION"). Not used to filter. |
| brand_name | TEXT | `device[].brand_name` | Free text. Used as evidence in manufacturer normalization. |
| manufacturer_name | TEXT | `device[].manufacturer_d_name` | Raw device manufacturer: 483 distinct spellings (474 after upper-casing and trimming). Use `report_features.manufacturer_group` instead. |
| model_number | TEXT | `device[].model_number` | Free text. |
| product_problems | TEXT | `product_problems` | FDA-coded problem terms, unique values joined with "; ". Empty in 122 reports. 331 distinct terms. |
| raw_json | TEXT | whole record | Complete original JSON, so any other field can be recovered without downloading again. |

### `narratives` (one row per text block)
| Column | Notes |
|---|---|
| mdr_report_key | Links to `reports`. |
| text_type_code | "Description of Event or Problem" (15,528 rows) or "Additional Manufacturer Narrative" (16,956 rows). |
| text | Free text, mostly upper case. Contains redactions such as `(B)(4)` and `(B)(6)` (FDA removes confidential or personal information). |

295 reports have no narrative at all; 297 have no event description.

### `download_log`
One row per download run: UTC time, query, total reported by the API, rows in the database.

## Analysis tables (`src/build_tables.py`)

### `report_features` (one row per report)
| Column | Notes |
|---|---|
| mdr_report_key | PK. |
| year, month | From `date_received` (`month` = YYYY-MM). |
| manufacturer_group | Normalized manufacturer (see rules below). |
| mfr_group_method | `name` (13,164 reports), `brand` (528), `raw` (454), `unknown` (88). |
| description | All "Description of Event or Problem" texts of the report, joined with a space. This is the input text for classification. |
| description_chars | Length of `description`. |

### `report_problems` (one row per report and FDA problem term)
16,821 rows. Lets SQL count problems directly. A report can have several problems, so counts by problem add up to more than the number of reports.

### `report_predictions` (`src/predict_all.py`)
One row per report with a description (13,937): `predicted_label` from the keyword model, `method` = `keywords_v1`. See `docs/model_card.md` for its accuracy and `docs/trends.md` for its calibration.

### `manufacturer_map`
Every combination of raw manufacturer name and brand, the assigned group and the method. Use it to audit the normalization.

## Manufacturer normalization rules
1. **By name:** substrings such as MASIMO/MASSIMO -> Masimo; NELLCOR/COVIDIEN/TYCO -> Covidien/Nellcor; PHILIPS/INVIVO -> Philips; and others listed in `src/build_tables.py`.
2. **By brand (only if the name gives no group):** names that are only a factory or contract manufacturer (e.g. "SANMINA-SCI SYSTEMS", "GALWAY (RP)-RX", "ST PAUL") are grouped using the brand (e.g. brand contains NELLCOR or OXIMAX -> Covidien/Nellcor; BCI -> Smiths Medical).
3. **Otherwise** the raw name is kept as its own group. Empty, "*", "UNK", "UNKNOWN" -> Unknown.

Limitation: corporate history (acquisitions, renamings) is **not** modeled. "Covidien/Nellcor" is one group across all years.

## Known data quality issues
- **Reporting is concentrated:** Masimo accounts for 6,868 of 14,234 reports (48%), and the 2014–2016 peak is mostly Masimo reports. Changes over time can reflect one company's reporting practice, not device performance.
- **Template narratives:** many descriptions are near-identical (e.g. 144 copies of one preventive-maintenance text). This matters for classification: near-duplicates in train and test inflate metrics.
- **Generic name is unreliable** (e.g. "BATTERY", "PUMP, INFUSION" with product code DQA), which is why the family is defined by product code.
- **Redactions** `(B)(4)`/`(B)(6)` replace confidential and personal details.

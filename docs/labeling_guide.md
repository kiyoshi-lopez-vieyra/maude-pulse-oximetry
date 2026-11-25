# Labeling guide

> **Status: final taxonomy, approved by the author on 2026-11-24** after testing it on real narratives. Every change is recorded in the decisions log at the end.

## Unit of labeling
One label per report (`mdr_report_key`), based **only** on the text in the `description` column (all "Description of Event or Problem" texts of the report). The manufacturer narrative is not used, because it is often written after the investigation and may contain the answer (root cause), which would make the task unrealistically easy.

## File
`labels/sample_to_label.xlsx` (300 reports, sheet `labels`; drop-down lists prevent typos). It was created from the CSV by `src/make_label_workbook.py` after the first 50 labels; the CSV is kept only as a backup of those first 50 labels. Fill in:
- `label`: one category code from the table below (required).
- `secondary_label`: a second category if the text clearly describes two failures (optional).
- `confidence`: 1 = guess, 2 = fairly sure, 3 = sure.
- `notes`: short reason for any hard case.

The manufacturer and the FDA problem codes are hidden on purpose, so they cannot influence the label.

## Failure taxonomy (draft)
| Code | Definition | Include | Exclude | Example (paraphrased) |
|---|---|---|---|---|
| `accuracy` | A reading is shown, but SpO2 or pulse rate is wrong. | High or low readings vs. blood gas, another monitor or clinical state; "inaccurate readings". | Unable to get any reading (`signal_acquisition`). | Monitor shows 60% while a second device shows over 90%. |
| `signal_acquisition` | The device cannot obtain or keep a reading. | No reading, intermittent or dropping values, "sensor off" or "searching" messages, failure to detect pulse. | Wrong but stable values (`accuracy`). | SpO2 value could not be displayed until the sensor was replaced. |
| `alarm` | The alarm or audio does not work as intended. | No alarm or tone, alarm too quiet, missed alarm, false or nuisance alarms. | An alarm that correctly reports another failure (label that failure). | Unit did not provide an audio tone. |
| `display` | The screen does not show information correctly. | Missing segments, blank or dim screen, lines, artifacts, frozen image. | Screen off because the device has no power (`power_battery`). | Display missing segments in the pulse-rate digits. |
| `power_battery` | Power supply problems. | Battery does not charge or drains early, device shuts off or will not turn on, AC/DC problems, docking power problems. | Reset with power still present (`software_behavior`). | Device turns itself off when moved. |
| `physical_damage` | Mechanical or material damage to the device, sensor or cable. | Broken or cracked housing, damaged cable or connector, exposed wires, loose or missing parts, corrosion, broken mount. | Damage that injures the patient (`patient_contact`). | Battery compartment separated during use. |
| `patient_contact` | Harm or risk from contact with the patient. | Skin redness, burns, pressure marks, rash, electric shock, overheating sensor on skin. | Harm caused by a missed alarm or wrong reading (label that failure). | Baby showed redness and skin rash after use. |
| `software_behavior` | The device behaves unexpectedly without a power, display or sensor cause. | Unexpected resets, freezes, screens changing by themselves, incorrect error messages, communication or connectivity errors. | | Device flips through screens when nobody touches it. |
| `other` | A clear device problem that fits none of the above. | Labeling or packaging errors, counterfeit or misleading product. | | Product sold online as a glucose meter. |
| `unclear` | Not enough information to decide. | "Device malfunctioned", "issue with the unit", text that only describes the patient. | | Unit was reported as faulty, no details. |

### Rule for two failures
Label the failure the reporter presents as the **main complaint** (usually the first one described). If it is truly impossible to choose, use this priority, ordered by potential for patient harm: `alarm` > `accuracy` > `signal_acquisition` > `patient_contact` > `power_battery` > `display` > `software_behavior` > `physical_damage`. Put the other one in `secondary_label`.

## Rules
- Label the **symptom the reporter observed**, not what you suspect happened or the root cause. Ask: "what did the person see?"
- A cause the reporter only suspects ("could have been corrosion") is **not** a label; write it in `notes`. A cause that was observed ("wires were frayed") can be the `secondary_label`.
- A number shown with no sensor on the patient ("SpO2 readings during probe-off") is `accuracy`: there is a number and it is false.
- If an alarm or page was sent but did not reach staff (failure of the hospital notification chain, outside the oximeter), do not label `alarm`; label the device failure and write the notification problem in `notes`.
- `alarm` includes **visual** alarms (e.g. "top light does not flash" on monitors whose top light is the alarm indicator), not only sound.
- Device **only turns off** ("shuts off by itself", "does not stay on") → `power_battery`. Device **turns off and back on by itself** ("turns on and off randomly") → `software_behavior`, because a device that switches itself on still has power.
- Error or service messages with no other detail are `software_behavior`; if the text says what failed ("battery error"), label that failure.
- `patient_contact` is only for harm from physical contact (burns, skin damage, shock). "Unknown if the patient was involved" is not a failure.
- `confidence` is an integer: 1, 2 or 3. If unsure between two values, use the lower one and explain in `notes`.
- `notes` is for doubts and reasons in hard cases; leave it empty when the label is clear. The patient outcome is already in the database (`event_type`).
- Do not look up the report's FDA codes or manufacturer while labeling.
- Save the workbook regularly and keep a backup copy.

## Process
- Sample: 300 reports drawn by `src/make_label_sample.py` (seed 42, exact duplicate texts removed, stratified: 60 before 2014, 120 in 2014–2019, 120 in 2020 or later).
- Planned evaluation split by date: train on reports received up to 2019, test on reports from 2020 onward. This mimics real use (a model built on the past, applied to new reports) and limits leakage from template texts.
- Labels are assigned **before** seeing any model prediction.
- Re-label 30 random reports after one week, without looking at the first labels, to check consistency: `python src/consistency.py --create` makes `labels/relabel_30.xlsx`; after labeling, `python src/consistency.py` reports agreement and Cohen's kappa. Result: TODO.
- Any labels suggested by a language model go in a separate column, are evaluated against the manual labels, and never replace them.

## Decisions log
| Date | Decision | Reason |
|------|----------|--------|
| 2026-11-24 | Draft taxonomy proposed (pending author review) | Based on reading a random sample of descriptions and the FDA problem terms |
| 2026-11-24 | Keep `accuracy` and `signal_acquisition` separate | They often share a cause (poor PPG signal), but the observed symptom and the risk differ: a wrong number that looks valid is a silent failure, while a missing reading is noticed by staff. Accuracy errors can also occur with a good signal (e.g. carboxyhemoglobin, skin pigmentation, calibration). |
| 2026-11-24 | Labeling moved from CSV to an Excel workbook with drop-down lists; typo in row 5 corrected (`signal_acquisitio` -> `signal_acquisition`) | Avoid typos; Excel also changed the date format in the CSV |
| 2026-11-24 | Rule refined: only turns off → `power_battery`; turns off and on by itself → `software_behavior` | Author's argument: a device that switches itself on has power, so the cycle looks like a reset |
| 2026-11-24 | Label audit of all 300 against the written rules (no model predictions used): 52 flagged: 45 changed and 7 kept with reasons; with the refined rule and the author's own corrections, 50 rows changed in total | Inconsistencies found in the first evaluation, mostly from fatigue and drop-down mis-clicks. Log: `labels/audit_log.csv`; pre-audit file kept as `labels/sample_to_label_v1_before_audit.xlsx` |
| 2026-11-24 | Rules clarified after the first labels (observed vs suspected cause, probe-off readings, notification chain, integer confidence) | Questions that came up while labeling rows 1–12 |

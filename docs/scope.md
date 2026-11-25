# Scope

> Keep this file updated if decisions change.

## Device family
- Devices: pulse oximeters
- FDA product code: **DQA** ("Oximeter", 21 CFR 870.2700, Class II), verified in the FDA Product Classification database.
- Included: reports where a device has product code DQA.
- Excluded: other codes whose generic name mentions "oximeter", e.g. MUD (tissue saturation oximeter, a different technology: NIRS instead of pulse photoplethysmography) and multiparameter monitors. Reason: keep failure categories comparable within one technology.
- Exploration on 2026-11-24 (`src/explore_api.py`): 13,519 reports had "oximeter" in the generic name; 11,780 of them (87%) were DQA.

## Time window (as used)
- Descriptive SQL queries: all reports, `date_received` 1991-12-31 to 2026-10-30.
- Growth comparison (Q6): complete years only, 2020–2022 vs 2023–2025.
- Control charts: baseline 2020-01 to 2022-12; monitoring 2023-01 to 2026-10 (FDA terms) or 2026-06 (predicted categories, because later reports often lack text).
- Why: recent years reflect current devices and reporting practice; early years have very few reports.

## Research questions
1. Which failure types are reported most often, and how do they change by year?
2. Which failure types grow fastest?
3. How well can a classifier assign the failure type from the report narrative?

## Limitations (keep these in every result)
- Passive reporting: reports are not validated; a report alone does not prove the device caused the event.
- Under-reporting is likely and device usage is unknown, so no incidence or rates.
- Growth in reports may reflect reporting changes (rules, awareness, media), not more failures.
- Duplicate or follow-up reports: each `mdr_report_key` appears once and follow-ups are stored inside the same record (`type_of_report`), so they do not create extra rows. Identical template narratives across different reports are common; they are removed before drawing the labeling sample.

## Out of scope
- Causal claims, comparisons of product safety between manufacturers, clinical recommendations.

## Decisions log
| Date | Decision | Reason |
|------|----------|--------|
| 2026-11-24 | Device family = product code DQA only | Homogeneous technology (pulse PPG), matches author's sensor expertise, 87% of oximeter reports |

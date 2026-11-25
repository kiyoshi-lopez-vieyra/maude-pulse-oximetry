# SQL queries: results and interpretation

Snapshot: 14,234 DQA reports downloaded 2026-11-24. SQL in `sql/`, full results in `results/queries/`.
All results were cross-checked with an independent pandas implementation (`tests/check_queries.py`, all checks pass).

**Reading rule for everything below:** these are counts of *reports* in a passive system. They do not measure how often oximeters fail, and they do not show that a device caused any harm.

| # | Question | Key result | Interpretation and caveats |
|---|---|---|---|
| 1 | Reports per year | Fewer than 50 per year before 2005; peak of 2,082 in 2015; 390–555 per year in 2020–2025; 967 in 2026 (partial year). | Volume changes a lot over time, so later queries use **shares**, not raw counts. |
| 2 | Event type per year | Malfunction is 92% of all reports (13,044). Injury 591, Death 365. | Event type is chosen by the reporter. A "Death" report means a death was mentioned, not that the oximeter caused it. |
| 3 | Who reports | Manufacturers submit 95.0% of reports; user facilities 2.9%; voluntary 2.1%. | The data mostly reflects manufacturers' complaint handling and coding habits. |
| 4 | Most frequent FDA problem terms | Incorrect Measurement (16.8% of reports), No Audible Alarm (9.8%), Display or Visual Feedback Problem (7.8%). | FDA terms are coded by the reporter, are overlapping (e.g. "Incorrect Measurement" vs "Low Readings"), and a report can have several. This motivates our own taxonomy from the narratives. |
| 5 | Share of top problems by period | "No Audible Alarm" is 38.9% of reports before 2014 but 1.3% in 2020–2026. "Incorrect Measurement" is 0.1% before 2014 and 23.4% in 2014–2019. | Such sharp jumps look like changes in **coding practice** (which term reporters choose) rather than in device behavior. Before 2014, 72% of reports (2,183 of 3,053) come from Covidien/Nellcor, and 1,123 of the 1,189 "No Audible Alarm" reports in that period are theirs, many with a standard "did not provide an audio tone" text. A problem missing from a period in the CSV means 0 reports. |
| 6 | Fastest-growing problems (2023–25 vs 2020–22, share of reports) | Unexpected Shutdown +15.1 percentage points (17 → 218 reports); Low Readings +6.4; Image Display Error/Artifact +5.7. Largest drops: Sensing Intermittently −9.3; Break −6.9. | The Unexpected Shutdown increase comes entirely from one manufacturer group (checked separately): a **signal worth investigating**, not proof of a design problem. |
| 7 | Manufacturer concentration | Masimo 48.3%, Covidien/Nellcor 25.3%, Philips 10.3%, Mediana 6.7%. | More reports usually reflect more devices in use and stricter reporting, not worse devices. Usage data is not available, so **no manufacturer comparison of safety is made**. |
| 8 | Share of each year from the largest group | Covidien/Nellcor 74–93% of reports in 2005–2011; Masimo 54–88% in 2014–2019; the largest group is at most 41.1% in 2024–2026. | The 2014–2017 peak is driven by one company's reporting. Trends must be checked per manufacturer before being interpreted. |
| 9 | Problems in Death/Injury reports | Device Alarm System (151 reports: 111 death, 40 injury), Patient-Device Incompatibility (105 injury), Adverse Event Without Identified Device or Use Problem (76). | Alarm problems are the most frequent term in harm reports, which is clinically plausible (a missed alarm delays response), but causality cannot be established from these reports. |
| 10 | Completeness of descriptions | Almost every report has a description until 2025. In 2026, 276 of 967 reports have no narrative text, all received July–October 2026. | Possibly the text is published later than the structured fields (not verified). **Action:** re-download in a few weeks and compare; until then, exclude reports without text from classification and treat the last months with caution. |

## Answers to the research questions
1. **Most frequent failure types:** measurement accuracy (incorrect, low or high readings), alarm problems and display problems dominate the FDA terms. Their shares change sharply over time, partly because of coding practice and manufacturer mix.
2. **Fastest growing (2023–2025 vs 2020–2022):** unexpected shutdown, low readings and display artifacts, each concentrated in specific manufacturers.
3. **Classification from text:** with 300 manual labels, keyword rules reach macro-F1 0.60 and TF-IDF + logistic regression 0.43 on reports from 2020 onward (`docs/model_card.md`). Good enough to support trend monitoring of some categories (`docs/trends.md`), not to classify single reports unsupervised.

# Trend detection with control charts

Two versions, made with the same script (`src/control_charts.py`):
1. **By FDA problem term** (`results/control_charts/`), the terms chosen by the reporter.
2. **By predicted failure category** (`results/control_charts_predicted/`), the author's taxonomy, assigned to every described report by the keyword model (`src/predict_all.py`; evaluation in `docs/model_card.md`).

## Method
- **Statistic:** for each month, the share of that month's DQA reports that include a given FDA problem term (p-chart). A share is used instead of a count because total report volume changes a lot from month to month.
- **Phase I (baseline):** January 2020 – December 2022. Center line = pooled share in the baseline.
- **Limits:** center ± 3 standard errors, recomputed for each month from that month's number of reports, so months with few reports have wider limits.
- **Phase II (monitoring):** January 2023 – October 2026. Two rules:
  1. a month above the upper limit;
  2. 8 consecutive months above the center line (a sustained shift).
- **Over-dispersion check (Laney p′):** reports are not independent (one complaint can produce several reports; one company files many similar reports), which makes binomial limits too narrow. `sigma_z` measures extra variation in the baseline (1 = none). Each rule-1 signal is also tested with limits widened by `sigma_z` (`survives_laney` in `results/control_charts/signals.csv`).

## 1. Results by FDA problem term (download of 2026-11-24)
| FDA problem term | Baseline share | sigma_z | Signals | Who reported most of the signal period |
|---|---|---|---|---|
| Unexpected Shutdown | 1.2% | 0.50 | Above the limit in most months since 2023 | Masimo (all 17 reports in 2022; all of the 2020–2025 increase) |
| Incorrect Measurement | 12.1% | 1.05 | 11 months above the limit, mostly 2026; sustained shift by Feb 2026 | Philips (153 of the 2026 reports with this term) |
| Low Readings | 8.2% | 1.27 | Several months in 2023–2026; sustained shift in 2024 | Covidien/Nellcor (57) and Mediana (52) in 2024 |
| High Readings | 4.5% | 1.04 | 5 months, 4 of them in 2026 | Philips (70 of 2026) |
| Device Alarm System | 8.1% | 1.40 | Aug, Sep, Oct and Dec 2025 (all survive the Laney check) | Covidien/Nellcor (51 of 57) |
| Sensing Intermittently | 12.6% | 1.18 | None | – |

## How to read this
- Each signal points to **a period and a manufacturer whose reports should be read**. It does not show that devices got worse: a recall, a new complaint-coding procedure or a batch of retrospective reports produces the same pattern.
- **Unexpected Shutdown:** the baseline itself is not stable (zero reports until March 2022, then a jump in April 2022), so Phase I is not "in control". The chart is better described as a **step change in 2022** that persisted, driven by one manufacturer. A proper next step is to read those narratives and check FDA recall records for the same period.
- Most signals in 2026 coincide with the change in reporting mix (Philips is the largest reporter in 2026, see `docs/queries.md` Q8).
- Charts: `results/control_charts/*.png`. Signals table: `results/control_charts/signals.csv`.

## Limitations
- FDA problem terms are chosen by the reporter, overlap, and change in use over time.
- Monthly counts are small (often 20–90 reports), so single-month signals are fragile; sustained shifts (rule 2) are more meaningful.
- Reports from July–October 2026 have structured fields but often no narrative yet (see `docs/queries.md` Q10); they are included here because these charts use structured fields only.

## 2. Results by predicted failure category

### How the categories were assigned
- `src/predict_all.py` applies the keyword rules to the 13,937 reports that have an event description (the 297 without one are excluded).
- The denominator of each month is the number of **described** reports, and the charts stop at **June 2026**, because many reports received July–October 2026 had no narrative yet in this download.
- The keyword model had macro-F1 0.60 on the labeled test set, so these charts show **predicted** shares, not true shares.

### Calibration: is each category over- or under-predicted?
On the 120 labeled test reports (2020+), predicted vs labeled counts (`results/classification/predicted_vs_true.csv`):

| Category | Labeled | Predicted | Reading |
|---|---|---|---|
| alarm | 14 | 16 | close |
| patient_contact | 20 | 19 | close |
| power_battery | 13 | 11 | close |
| physical_damage | 7 | 5 | close (small n) |
| display | 4 | 9 | over-predicted (small n) |
| accuracy | 37 | 16 | **strongly under-predicted** |
| signal_acquisition | 11 | 5 | under-predicted |
| software_behavior | 10 | 4 | under-predicted |
| no keyword match | 0 | 34 | 28% of test reports get no category |

So the **level** of `accuracy`, `signal_acquisition` and `software_behavior` in these charts is too low. **Changes over time** remain informative only if that bias is stable over time, which cannot be verified with 120 labeled reports. The most trustworthy charts are `alarm`, `patient_contact` and `power_battery`.

### Results (baseline 2020–2022, monitoring 2023–June 2026)
| Predicted category | Baseline share | sigma_z | Signals | Who reported most of the signal period | Agrees with FDA-term chart? |
|---|---|---|---|---|---|
| alarm | 10.0% | 1.24 | Jul, Aug, Sep, Oct, Dec 2025 (4 also with Laney limits) | Covidien/Nellcor (55 of 80 predicted alarm reports in Jul–Dec 2025) | **Yes**: same period and manufacturer as "Device Alarm System" |
| power_battery | 7.6% | 1.18 | Apr and Oct 2023, Jun 2025; sustained shift by Aug 2023 | Masimo (46 of 48 in Apr–Oct 2023) | **Yes**: matches the "Unexpected Shutdown" step change |
| patient_contact | 8.1% | 1.73 | Sustained shift during 2023 (8 months above center by Dec 2023); 7 single months above the limit, only Aug 2024 also with Laney limits | Mixed: Covidien/Nellcor 30, Masimo 25, Mediana 15 in 2023 | **New**: not visible in the FDA-term charts |
| accuracy | 16.8% | 1.40 | Feb and May 2024, Jan 2026 (plus Nov 2024 only without Laney) | Philips and Masimo in Jan 2026 | Partly: the FDA-term charts show more signals in 2026 |
| software_behavior | 2.5% | 0.94 | Jul 2023, May 2026 | – | Unreliable: keyword recall for this category was 0.10 |
| signal_acquisition | 5.9% | 1.48 | Jun 2026 only, not with Laney limits | – | – |
| display | 8.8% | 1.20 | None | – | – |
| physical_damage | 5.1% | 1.25 | None | – | – |

### Reading these results
- **Two signals are confirmed by both methods** (alarm in late 2025, power/shutdown in 2023). When two independent codings, the reporter's FDA term and our text classification, point to the same period and manufacturer, the signal is more credible.
- **One new signal appears only with our taxonomy:** a sustained rise of patient-contact reports (burns, blisters, pressure injuries) during 2023, spread across several manufacturers rather than one. Most single months do not survive the Laney check, so this is a *sustained shift worth reading*, not a strong alarm. The FDA terms split these events across several terms, which may be why the FDA-term view does not show it.
- **Cross-check of the keyword model:** of the 218 reports with the FDA term "Unexpected Shutdown" in 2023–2025, the keywords classified 118 as `power_battery`, 78 got no category and 16 went to `software_behavior`. Reading the misses showed phrasings the rules do not cover ("turning off", "will turn on/off at random"). Improving the rules now and re-testing on the same labels would overfit them to the test set; a fair update needs new labeled reports.

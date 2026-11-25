# Complaint-handling flow (inspired by ISO 13485:2016, 8.2.2 and 8.2.3)

> A simplified, generic flow for learning purposes; not a procedure for any real organization.

```
Complaint received ──► 1. Record ──► 2. Is it a complaint? ──no──► document reason, close
                                         │yes
                                         ▼
                         3. Must it be reported to the regulator? ──yes──► 4. Report (e.g. FDA MDR)
                                         │                                     │
                                         ▼                                     ▼
                         5. Investigate (or document why not) ◄────────────────┘
                                         │
                                         ▼
                         6. Correction / corrective action if needed
                                         │
                                         ▼
                         7. Trend all complaints ──► 8. Feed risk management (see post_market_risk_review.md)
```

| Step | What a manufacturer does | How this project's tools could support it | Limit of the support |
|---|---|---|---|
| 1. Record | Capture device, date, reporter, description, outcome. | `docs/data_dictionary.md` shows which fields MAUDE keeps and how complete they are (e.g. event date missing in 15.8% of reports). | MAUDE is the regulator's copy, not the complaint file. |
| 3. Reportability | Decide if the event must be reported (e.g. death, serious injury, malfunction that could cause them). | Not supported. | Reportability is a regulated decision by trained staff; no model should make it. |
| 5. Investigate | Find the root cause, often by testing the returned device. | The failure-type classifier (`src/classify.py`, `src/predict_all.py`) could pre-sort narratives so investigators see similar past cases. | Suggestion only (macro-F1 0.60); the narrative rarely contains the root cause. |
| 7. Trend | Analyze complaints over time to detect emerging problems. | `src/control_charts.py`: p-charts of monthly shares by FDA term and by predicted failure category, with sustained-shift rules and an over-dispersion check. | Signals are prompts to investigate, not conclusions. |
| 8. Risk feedback | Use trends to update hazard analysis and risk controls. | `post_market_risk_review.md`. | Needs real usage data (units in the field) to estimate probability. |

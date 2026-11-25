# Mini regulatory dossier (inspired by ISO 13485 and ISO 14971)

> **Status: reviewed by the author on 2026-11-24** (severity ratings approved).
> This dossier is a learning exercise **inspired by** ISO 13485:2016 (complaint handling, clause 8.2.2; reporting to regulatory authorities, clause 8.2.3) and ISO 14971:2019 (production and post-production activities, clause 10). It **does not claim compliance** with any standard or regulation, it was not written by or for a manufacturer, and it uses only public MAUDE data. The standards themselves are copyrighted and are not reproduced here; only their general structure is referenced.

## Why this exists
A manufacturer receives complaints, decides which must be reported to the regulator, investigates them, and feeds what it learns back into risk management. MAUDE is the public end of that chain. This project works backwards from MAUDE to show how data and code could support the post-market part of the process.

## Contents
| File | What it shows |
|---|---|
| [`complaint_handling.md`](complaint_handling.md) | A complaint-handling flow and where each tool of this project could help. |
| [`post_market_risk_review.md`](post_market_risk_review.md) | Post-market risk review: approved severity per failure category, MAUDE evidence by predicted category, and the trend signals found. |

## Regulatory context checked on 2026-11-24
- FDA product code **DQA** ("Oximeter"), 21 CFR 870.2700, Class II (FDA Product Classification database).
- FDA issued a **draft** guidance on 7 January 2025, *Pulse Oximeters for Medical Purposes: Non-Clinical and Clinical Performance Testing, Labeling, and Premarket Submission Recommendations*, motivated in part by evidence of accuracy differences across skin pigmentation. Whether it has been finalized since then was **not verified**; check the FDA pulse oximeters page before citing it.

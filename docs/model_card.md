# Model card: failure-type classifier for pulse oximeter MAUDE reports

> Results of 2026-11-24, after the label audit (v2). Numbers are reported as they came out; nothing was tuned on the test set.

## Model details
- **Task:** assign one failure category (see `docs/labeling_guide.md`) to the event description of an FDA MAUDE report for pulse oximeters (product code DQA).
- **Models compared** (`src/classify.py`):
  1. *Majority class*: always predicts the most frequent training label (the floor to beat).
  2. *Keyword rules*: hand-written patterns, fixed on 2026-11-24 before any manual label existed.
  3. *TF-IDF + logistic regression*: words and word pairs, balanced class weights, fixed hyper-parameters.
- **Author:** Alfonso Kiyoshi López Vieyra (labels and decisions); code written with an AI assistant (Claude), reviewed by the author.

## Intended use
- Help an analyst triage and count report narratives by failure type, so trends can be monitored per failure type.
- Portfolio and learning project.

## Out of scope
- Clinical decisions about any patient or device.
- Deciding whether an event is reportable to a regulator, or replacing a manufacturer's complaint investigation.
- Comparing the safety of manufacturers or products.

## Data
- **Source:** openFDA device adverse event API (MAUDE), product code DQA, downloaded 2026-11-24 (14,234 reports).
- **Labeled set:** 300 descriptions (`labels/sample_to_label.xlsx`), exact duplicate texts removed, stratified by period (60 before 2014, 120 in 2014–2019, 120 in 2020+). Labeled by the author, blind to manufacturer and FDA problem codes.
- **Split by date:** train = 180 reports received up to 2019; test = 120 reports received 2020 or later.
- **Label distribution (v2):**

| Category | Train | Test |
|---|---|---|
| accuracy | 48 | 37 |
| alarm | 35 | 14 |
| power_battery | 30 | 13 |
| display | 28 | 4 |
| software_behavior | 15 | 10 |
| signal_acquisition | 10 | 11 |
| patient_contact | 9 | 20 |
| physical_damage | 3 | 7 |
| other | 1 | 4 |
| unclear | 1 | 0 |

The mix changes a lot between periods (e.g. `patient_contact` 9 vs 20, `display` 28 vs 4), which is part of what the date split is meant to test.

## Label quality and audit
- **Audit (2026-11-24):** after the first evaluation, all 300 labels were checked against the written rules of the labeling guide, **without using model predictions**. The AI assistant read every description independently (`labels/claude_reading.csv`) and flagged 52 labels that contradicted a written rule. The author decided each case; the assistant applied the decisions.
- **Result:** of the 52 flagged labels, the author changed 45 and kept 7 (with reasons). Applying the refined rule changed one more row, one kept label received a secondary label, and the author corrected 3 rows on his own: 50 rows changed in total (`labels/audit_log.csv`). Rule refined: "only turns off" → `power_battery`; "turns off and on by itself" → `software_behavior`.
- **Main cause of inconsistencies:** probably fatigue and drop-down mis-clicks. Agreement between the author's labels and the assistant's independent reading was 88% in the first 50 rows (labeled while discussing the rules) and 58–76% in later blocks of 50.
- **Pre-audit labels are kept** (`labels/sample_to_label_v1_before_audit.xlsx`) and their results are reported below.
- **Consistency re-test:** 30 random reports to be re-labeled blind by the author after one week (`src/consistency.py`, `labels/relabel_30.xlsx`): TODO.
- **Confidence:** the author marked 289 of 300 labels as confidence 3, 11 as 2.

## Metrics (test set, date split)
| Labels | Model | Accuracy | Macro-F1 | 95% CI (bootstrap) |
|---|---|---|---|---|
| v2 (after audit) | Majority | 0.308 | 0.052 | 0.041–0.063 |
| v2 (after audit) | **Keywords** | **0.567** | **0.602** | 0.483–0.698 |
| v2 (after audit) | TF-IDF + LogReg | 0.533 | 0.425 | 0.331–0.496 |
| v1 (before audit) | Majority | 0.283 | 0.049 | 0.038–0.060 |
| v1 (before audit) | Keywords | 0.492 | 0.496 | 0.401–0.568 |
| v1 (before audit) | TF-IDF + LogReg | 0.442 | 0.350 | 0.252–0.428 |

Macro-F1 averages over the classes present in the test set (9 in v2; `unclear` has no test example). Lenient accuracy (prediction equals the primary or the secondary label) differs by at most 0.01 from accuracy.
Secondary check, 5-fold cross-validation over all years (optimistic, no date split), v2: keywords 0.546, TF-IDF 0.477.

**Per-class F1 (v2, test):**

| Category (test n) | Keywords | TF-IDF |
|---|---|---|
| patient_contact (20) | 0.92 | 0.77 |
| power_battery (13) | 0.75 | 0.71 |
| alarm (14) | 0.73 | 0.26 |
| physical_damage (7) | 0.67 | 0.17 |
| signal_acquisition (11) | 0.63 | 0.22 |
| display (4) | 0.62 | 0.50 |
| accuracy (37) | 0.57 | 0.62 |
| other (4) | 0.40 | 0.00 |
| software_behavior (10) | 0.14 | 0.57 |

Confusion matrices: `results/classification/confusion_*.png`. Errors: `results/classification/errors_tfidf.csv`.

## Interpretation
- Both models beat the floor clearly, but neither is reliable enough to run unsupervised: about half of the test reports are misclassified.
- **Keyword rules beat TF-IDF on this data.** With 180 training texts spread over 10 classes, TF-IDF has too few examples per class (3 for `physical_damage`), while the keyword rules carry domain knowledge written in advance. TF-IDF is better only for `software_behavior` and slightly for `accuracy`, the two classes whose wording is varied and hard to capture with fixed patterns.
- **Keywords miss "accuracy" often** (precision 0.94 but recall 0.41): many inaccurate-reading reports use wording the rules do not cover.
- The confidence intervals are wide (about ±0.1), so differences smaller than that should not be over-interpreted.

## Important caveat about the improvement after the audit
The scores rose after the audit (keywords 0.50 → 0.60 macro-F1). This must **not** be read as purely "cleaner labels". The same AI assistant wrote the keyword rules and flagged the labels in the audit, both based on the same written guide. Labels moved toward the guide's wording, which is also what the keyword rules encode, so part of the gain for keywords may come from this shared source. Mitigations: the audit did not use model predictions, the author decided every case (and kept 7), and both versions are reported. An independent second labeler would be the proper fix.

## Limitations and risks
- Small data: 120 test reports; classes with fewer than 5 training examples (`physical_damage`, `other`, `unclear`) are unreliable.
- Distribution shift over time in manufacturers, coding practice and failure mix (see `docs/queries.md`).
- Template texts: 1 of 120 test reports is a near-copy (cosine ≥ 0.9) of a training report.
- Single labeler; no inter-annotator agreement.
- Narratives are written by reporters, mostly manufacturers, and may be incomplete.
- Recent reports may lack text (July–October 2026 in this snapshot).

## Use of an AI assistant (documented as required by the project rules)
- Code, documentation drafts and the label audit were produced with Claude and reviewed by the author.
- The assistant's independent reading of the 300 descriptions (`labels/claude_reading.csv`) agreed with the author's pre-audit labels in 210 of 300 cases (70%). This is **not** a clean "LLM vs. expert" result: the assistant had discussed about 25 of these reports with the author while the rules were being defined, and it later acted as auditor. A clean comparison would need a model that has never seen the labels.

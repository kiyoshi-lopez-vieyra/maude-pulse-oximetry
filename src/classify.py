"""Classify the failure type of a report from its event description.

Run from the project root, after labeling:  python src/classify.py
Optional: python src/classify.py --labels path/to/labels.csv --out results/classification

Inputs
- labels/sample_to_label.xlsx (or .csv): the manual labels (only rows with a `label` are used).
- data/maude.db: for nothing else than checking the report keys exist.

Models (all hyper-parameters are FIXED in advance; nothing is tuned on the test set)
1. majority: always predicts the most frequent training label (the floor to beat).
2. keywords: hand-written rules per category (KEYWORDS below). Written on 2026-11-24,
   BEFORE any manual label existed, so they cannot be fitted to the labels.
3. tfidf_logreg: TF-IDF of words and word pairs + logistic regression with balanced
   class weights.

Evaluation
- Split by date: train on reports received up to 2019, test on reports from 2020 on.
  This mimics real use (model built on the past, applied to new reports).
- Per-class precision, recall and F1, macro-F1, accuracy, and a bootstrap 95%
  confidence interval for macro-F1 (the test set is small, so the uncertainty is large).
- "Lenient" accuracy: a prediction also counts as correct if it equals the secondary label.
- Secondary: 5-fold stratified cross-validation on ALL labeled reports (mixes years,
  so it is optimistic; reported only to show how unstable a single small test set is).
- Leakage check: how many test texts are near-copies (cosine >= 0.9) of a training text.
- Confusion matrices (PNG) and a CSV with every test error for manual error analysis.
"""

import argparse
import csv
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support  # noqa: E402
from sklearn.metrics.pairwise import cosine_similarity  # noqa: E402
from sklearn.model_selection import StratifiedKFold  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "maude.db"
# The Excel workbook (with drop-downs) is used when it exists; otherwise the CSV.
DEFAULT_LABELS = PROJECT_ROOT / "labels" / "sample_to_label.xlsx"
if not DEFAULT_LABELS.exists():
    DEFAULT_LABELS = PROJECT_ROOT / "labels" / "sample_to_label.csv"
DEFAULT_OUT = PROJECT_ROOT / "results" / "classification"
TEST_FROM_YEAR = 2020
SEED = 42
N_BOOTSTRAP = 1000

CATEGORIES = [
    "accuracy", "signal_acquisition", "alarm", "display", "power_battery",
    "physical_damage", "patient_contact", "software_behavior", "other", "unclear",
]
# Tie-break order for the keyword model (same priority as the labeling guide).
PRIORITY = [
    "alarm", "accuracy", "signal_acquisition", "patient_contact", "power_battery",
    "display", "software_behavior", "physical_damage", "other",
]
KEYWORDS = {
    "accuracy": [r"inaccurate", r"incorrect (spo2|reading|value|measurement)", r"false (reading|value)",
                 r"\b(low|high)(er)? (than expected )?(spo2|reading|value|saturation)", r"discrepan",
                 r"\babg\b", r"blood gas", r"compared (to|with)", r"difference of", r"\bnot accurate"],
    "signal_acquisition": [r"no (reading|signal|pulse|value)", r"unable to (obtain|get|read|pick)",
                           r"(could|would) not (read|obtain|pick|detect|display the)", r"intermittent(ly)? (reading|signal)",
                           r"drop(ped|s|ping)? ?(out|spo2|waveform)", r"poor signal", r"sensor off", r"searching",
                           r"not (reading|picking up)", r"loss of signal", r"low perfusion"],
    "alarm": [r"alarm", r"audio", r"audible", r"\btone\b", r"\bbeep", r"volume", r"speaker"],
    "display": [r"display", r"screen", r"segment", r"\blcd\b", r"\bled\b", r"blank", r"dim\b", r"backlight"],
    "power_battery": [r"batter", r"charg", r"power(s|ed)? (off|down|on)", r"turn(s|ed)? (itself )?off",
                      r"shut(s|ting)? (off|down)", r"will not turn on", r"won'?t turn on", r"\bac\b", r"dock"],
    "physical_damage": [r"broke", r"crack", r"fray", r"exposed wire", r"damage", r"loose", r"corro",
                        r"missing (piece|part|cover)", r"separat", r"bent", r"torn"],
    "patient_contact": [r"burn", r"blister", r"redness", r"rash", r"skin", r"pressure (injury|ulcer|mark)",
                        r"shock", r"irritation", r"\bhot\b", r"overheat"],
    "software_behavior": [r"reset", r"reboot", r"freez", r"froze", r"error (message|code)", r"software",
                          r"lock(ed|s)? up", r"by itself", r"communicat", r"not respond"],
    "other": [r"label", r"packag", r"counterfeit", r"advertis", r"instruction"],
}
_COMPILED = {cat: [re.compile(p) for p in pats] for cat, pats in KEYWORDS.items()}


def clean(text):
    text = text.lower()
    text = re.sub(r"\(b\)\s*\(\d\)", " redacted ", text)  # FDA redactions (B)(4), (B)(6)
    return re.sub(r"\s+", " ", text).strip()


def keyword_predict(texts):
    preds = []
    for t in texts:
        scores = {cat: sum(1 for p in pats if p.search(t)) for cat, pats in _COMPILED.items()}
        best = max(scores.values())
        if best == 0:
            preds.append("unclear")
        else:
            preds.append(next(c for c in PRIORITY if scores.get(c) == best))
    return preds


def read_xlsx(path):
    """Read the 'labels' sheet of the labeling workbook into a list of dicts of strings."""
    from openpyxl import load_workbook
    ws = load_workbook(path, read_only=True, data_only=True)["labels"]
    rows = list(ws.iter_rows(values_only=True))
    header = [str(h) for h in rows[0]]
    return [{h: ("" if v is None else str(v)) for h, v in zip(header, r)} for r in rows[1:] if any(r)]


def read_csv_any(path):
    """Read the labels CSV as Excel may save it: UTF-8 or Windows-1252, comma or semicolon."""
    raw = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    first_line = text.splitlines()[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    return list(csv.DictReader(text.splitlines(), delimiter=delimiter))


def load_labels(path):
    reader = read_xlsx if str(path).lower().endswith(".xlsx") else read_csv_any
    rows = [r for r in reader(path) if (r.get("label") or "").strip()]
    # Excel can reformat dates and keys, so take the date from the database when possible.
    db_dates = {}
    if DB_PATH.exists():
        db_dates = dict(sqlite3.connect(DB_PATH).execute("SELECT mdr_report_key, date_received FROM reports"))
    for r in rows:
        r["mdr_report_key"] = r["mdr_report_key"].strip()
        r["label"] = r["label"].strip().lower()
        r["secondary_label"] = (r.get("secondary_label") or "").strip().lower()
        date = db_dates.get(r["mdr_report_key"]) or r["date_received"]
        match = re.search(r"(19|20)\d\d", date)
        if not match:
            sys.exit(f"Cannot read the date of report {r['mdr_report_key']}: '{date}'")
        r["date_received"] = date
        r["year"] = int(match.group(0))
    bad = sorted({r["label"] for r in rows} - set(CATEGORIES))
    bad_sec = sorted({r["secondary_label"] for r in rows if r["secondary_label"]} - set(CATEGORIES))
    if bad or bad_sec:
        sys.exit(f"Unknown label codes (check spelling): {bad + bad_sec}. Allowed: {CATEGORIES}")
    for r in rows:
        r["text"] = clean(r["description"])
    return rows


def evaluate(name, y_true, y_pred, y_secondary, labels, rng):
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    y_true_a, y_pred_a = np.array(y_true), np.array(y_pred)
    # Macro-F1 only over classes present in this test set: a class with no test
    # examples cannot be evaluated and would add an artificial 0.
    eval_labels = [lab for lab in labels if lab in set(y_true)]
    macro = f1_score(y_true_a, y_pred_a, labels=eval_labels, average="macro", zero_division=0)
    boot = []
    for _ in range(N_BOOTSTRAP):
        idx = rng.integers(0, len(y_true_a), len(y_true_a))
        boot.append(f1_score(y_true_a[idx], y_pred_a[idx], labels=eval_labels, average="macro", zero_division=0))
    lenient = np.mean([bool(pr == t or (sec != "" and pr == sec))
                       for pr, t, sec in zip(y_pred, y_true, y_secondary)])
    return {
        "model": name,
        "accuracy": round(float(np.mean(y_true_a == y_pred_a)), 3),
        "lenient_accuracy": round(float(lenient), 3),
        "macro_f1": round(float(macro), 3),
        "macro_f1_classes": eval_labels,
        "macro_f1_ci95": [round(float(np.percentile(boot, 2.5)), 3), round(float(np.percentile(boot, 97.5)), 3)],
        "per_class": {lab: {"precision": round(float(p[i]), 3), "recall": round(float(r[i]), 3),
                            "f1": round(float(f[i]), 3), "support": int(s[i])} for i, lab in enumerate(labels)},
    }


def plot_confusion(y_true, y_pred, labels, title, path):
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    fig, ax = plt.subplots(figsize=(8, 7), facecolor="#fcfcfb")
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(labels)), labels, fontsize=9)
    for i in range(len(labels)):
        for j in range(len(labels)):
            if cm[i, j]:
                ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=9,
                        color="white" if cm[i, j] > cm.max() / 2 else "#0b0b0b")
    ax.set_xlabel("Predicted", color="#52514e")
    ax.set_ylabel("Manual label", color="#52514e")
    ax.set_title(title, loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default=str(DEFAULT_LABELS))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows = load_labels(args.labels)
    if len(rows) < 30:
        sys.exit(f"Only {len(rows)} labeled rows. Label at least 30 before running.")
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        keys = {k for (k,) in conn.execute("SELECT mdr_report_key FROM reports")}
        missing = [r["mdr_report_key"] for r in rows if r["mdr_report_key"] not in keys]
        if missing:
            print(f"WARNING: {len(missing)} labeled keys are not in the database, e.g. {missing[:3]}")

    train = [r for r in rows if r["year"] < TEST_FROM_YEAR]
    test = [r for r in rows if r["year"] >= TEST_FROM_YEAR]
    print(f"Labeled: {len(rows)}  train (<{TEST_FROM_YEAR}): {len(train)}  test (>={TEST_FROM_YEAR}): {len(test)}")
    print("Train label counts:", dict(Counter(r["label"] for r in train).most_common()))
    print("Test label counts: ", dict(Counter(r["label"] for r in test).most_common()))
    if not train or not test:
        sys.exit("Need labeled reports on both sides of the date split.")

    labels = [c for c in CATEGORIES if any(r["label"] == c for r in rows)]
    y_tr, y_te = [r["label"] for r in train], [r["label"] for r in test]
    sec_te = [r["secondary_label"] for r in test]
    x_tr, x_te = [r["text"] for r in train], [r["text"] for r in test]

    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    X_tr, X_te = vec.fit_transform(x_tr), vec.transform(x_te)
    clf = LogisticRegression(max_iter=5000, class_weight="balanced", C=1.0)
    clf.fit(X_tr, y_tr)

    majority = Counter(y_tr).most_common(1)[0][0]
    preds = {
        "majority": [majority] * len(test),
        "keywords": keyword_predict(x_te),
        "tfidf_logreg": list(clf.predict(X_te)),
    }
    proba = clf.predict_proba(X_te).max(axis=1)

    rng = np.random.default_rng(SEED)
    results = [evaluate(name, y_te, p, sec_te, labels, rng) for name, p in preds.items()]

    # Secondary: out-of-fold predictions with 5-fold stratified CV over all years.
    y_all = np.array([r["label"] for r in rows])
    x_all = [r["text"] for r in rows]
    oof = np.empty(len(rows), dtype=object)
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # tiny classes trigger a split warning; reported below
        for tr_idx, te_idx in folds.split(x_all, y_all):
            v = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
            m = LogisticRegression(max_iter=5000, class_weight="balanced", C=1.0)
            m.fit(v.fit_transform([x_all[i] for i in tr_idx]), y_all[tr_idx])
            oof[te_idx] = m.predict(v.transform([x_all[i] for i in te_idx]))
    cv = {
        "note": "5-fold stratified CV over all years; optimistic (no date split)",
        "tfidf_logreg_macro_f1": round(float(f1_score(y_all, oof.astype(str), labels=labels,
                                                      average="macro", zero_division=0)), 3),
        "keywords_macro_f1": round(float(f1_score(y_all, keyword_predict(x_all), labels=labels,
                                                  average="macro", zero_division=0)), 3),
    }

    sims = cosine_similarity(X_te, X_tr).max(axis=1)
    leakage = {"threshold": 0.9, "test_near_copies_of_train": int((sims >= 0.9).sum()), "n_test": len(test)}
    small = [c for c in labels if sum(1 for y in y_tr if y == c) < 5]

    report = {"n_labeled": len(rows), "n_train": len(train), "n_test": len(test),
              "test_from_year": TEST_FROM_YEAR, "classes_with_fewer_than_5_train_examples": small,
              "leakage_check": leakage, "models": results, "secondary_cv_all_years": cv}
    (out / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    plot_confusion(y_te, preds["tfidf_logreg"], labels, "TF-IDF + logistic regression (test, 2020+)",
                   out / "confusion_tfidf.png")
    plot_confusion(y_te, preds["keywords"], labels, "Keyword rules (test, 2020+)", out / "confusion_keywords.png")

    with (out / "errors_tfidf.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["mdr_report_key", "date_received", "label", "secondary_label", "predicted",
                    "model_confidence", "keyword_prediction", "max_similarity_to_train", "description"])
        for i, r in enumerate(test):
            if preds["tfidf_logreg"][i] != r["label"]:
                w.writerow([r["mdr_report_key"], r["date_received"], r["label"], r["secondary_label"],
                            preds["tfidf_logreg"][i], round(float(proba[i]), 2), preds["keywords"][i],
                            round(float(sims[i]), 2), r["description"]])

    print("\nTest results (date split):")
    print(f"  {'model':<14}{'accuracy':>9}{'lenient':>9}{'macro-F1':>10}   95% CI")
    for res in results:
        ci = res["macro_f1_ci95"]
        print(f"  {res['model']:<14}{res['accuracy']:>9.3f}{res['lenient_accuracy']:>9.3f}"
              f"{res['macro_f1']:>10.3f}   [{ci[0]:.3f}, {ci[1]:.3f}]")
    print(f"\nSecondary (5-fold CV, all years, optimistic): TF-IDF macro-F1 {cv['tfidf_logreg_macro_f1']:.3f}, "
          f"keywords macro-F1 {cv['keywords_macro_f1']:.3f}")
    print(f"Near-copies of training texts in test: {leakage['test_near_copies_of_train']} of {len(test)}")
    if small:
        print(f"Classes with fewer than 5 training examples (unreliable): {small}")
    print(f"Saved metrics.json, confusion matrices and errors_tfidf.csv to {out}")


if __name__ == "__main__":
    main()

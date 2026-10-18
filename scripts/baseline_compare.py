"""How much does the trained model add over simple rules and tiny decision trees?

    docker run -i --rm --network none -v $PWD/data:/app/data:ro \
        -v $PWD/artifacts:/app/artifacts:ro -v $PWD/results:/app/results \
        shieldz:latest python scripts/baseline_compare.py

Same time-based holdout as results/MODEL_CARD.md (step > 600).
Writes results/baseline_comparison.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import xgboost as xgb
from sklearn.metrics import average_precision_score
from sklearn.tree import DecisionTreeClassifier

from shieldz.config import model_dir
from shieldz.contracts import FEATURE_ORDER
from shieldz.model.data import load_paysim, time_based_split

X, y, step = load_paysim()
Xtr, ytr, Xt, yt = time_based_split(X, y, step, split_step=600)
cols, yt = list(FEATURE_ORDER), yt.to_numpy()
rows: list[tuple[str, str]] = []


def add(name: str, flag, pr_auc: float | None = None) -> None:
    flag = np.asarray(flag).astype(bool)
    tp, fp = int((flag & (yt == 1)).sum()), int((flag & (yt == 0)).sum())
    fn = int((~flag & (yt == 1)).sum())
    auc = f"{pr_auc:.4f}" if pr_auc is not None else "n/a"
    cells = [name, f"{tp}/{tp + fn}", f"{tp / (tp + fn):.4f}", f"{fp:,}"]
    cells += [f"{tp / max(tp + fp, 1):.3f}", auc]
    rows.append((name, "| " + " | ".join(cells) + " |"))


risky = (Xt["type_TRANSFER"] == 1) | (Xt["type_CASH_OUT"] == 1)
drain = Xt["drains_account"] == 1
add("Rule: TRANSFER/CASH_OUT, account drained", risky & drain)
add(
    "Rule: the above, and payee balance is zero",
    risky & drain & (Xt["payee_balance_before_zero"] == 1),
)
add("Rule: TRANSFER/CASH_OUT, amount >= 99% of balance", risky & (Xt["amount_to_balance"] >= 0.99))
for depth in (2, 3, 4):
    tree = DecisionTreeClassifier(max_depth=depth, class_weight="balanced", random_state=0)
    p = tree.fit(Xtr[cols], ytr).predict_proba(Xt[cols])[:, 1]
    add(f"Decision tree, depth {depth} (learned if/else)", p >= 0.5, average_precision_score(yt, p))
booster = xgb.Booster()
booster.load_model(str(model_dir() / "model.json"))
score = booster.predict(xgb.DMatrix(Xt[cols].to_numpy(), feature_names=cols))
t_block = json.loads((model_dir() / "thresholds.json").read_text())["t_block"]
add(
    f"**ShieldZ XGBoost** (block at {t_block})",
    score >= t_block,
    average_precision_score(yt, score),
)

lines = [
    "# Baseline comparison: what does the model add?",
    "",
    f"Time-based holdout (step > 600): {len(yt):,} rows, {int(yt.sum()):,} fraud. "
    "Produced by `scripts/baseline_compare.py` on the LinuxONE VM.",
    "",
    "| Detector | Fraud caught | Recall | False alarms | Precision | PR-AUC |",
    "|---|---|---|---|---|---|",
    *[r[1] for r in rows],
    "",
    "**Reading it.** Obvious hand-written rules are poor (tens of thousands of false alarms, "
    "because many legitimate PaySim transfers also empty an account). But a learned decision tree "
    "of depth 3 matches our XGBoost model and depth 4 beats it. PaySim fraud is close to a "
    "threshold pattern, so the model is not where ShieldZ's value is. We claim the architecture "
    "(privacy barrier, leak audit, signed audit trail, on-platform real-time decisions), not "
    "detection accuracy.",
]
Path("results/baseline_comparison.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))

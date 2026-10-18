# Baseline comparison: what does the model add?

Time-based holdout (step > 600): 103,573 rows, 1,600 fraud. Produced by `scripts/baseline_compare.py` on the LinuxONE VM.

| Detector | Fraud caught | Recall | False alarms | Precision | PR-AUC |
|---|---|---|---|---|---|
| Rule: TRANSFER/CASH_OUT, account drained | 1542/1600 | 0.9637 | 37,063 | 0.040 | n/a |
| Rule: the above, and payee balance is zero | 1014/1600 | 0.6338 | 6,269 | 0.139 | n/a |
| Rule: TRANSFER/CASH_OUT, amount >= 99% of balance | 1542/1600 | 0.9637 | 37,114 | 0.040 | n/a |
| Decision tree, depth 2 (learned if/else) | 1542/1600 | 0.9637 | 1 | 0.999 | 0.9645 |
| Decision tree, depth 3 (learned if/else) | 1591/1600 | 0.9944 | 5 | 0.997 | 0.9945 |
| Decision tree, depth 4 (learned if/else) | 1599/1600 | 0.9994 | 4 | 0.998 | 0.9994 |
| **ShieldZ XGBoost** (block at 0.75) | 1598/1600 | 0.9988 | 79 | 0.953 | 0.9944 |

**Reading it.** Obvious hand-written rules are poor (tens of thousands of false alarms, because many legitimate PaySim transfers also empty an account). But a learned decision tree of depth 3 matches our XGBoost model and depth 4 beats it. PaySim fraud is close to a threshold pattern, so the model is not where ShieldZ's value is. We claim the architecture (privacy barrier, leak audit, signed audit trail, on-platform real-time decisions), not detection accuracy.

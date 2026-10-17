# Model Card: ShieldZ Fraud Detection Engine

## Overview
- **Model Name**: `xgboost` (`xgb-v1`)
- **Algorithm**: XGBoost (`tree_method='hist'`)
- **Primary Objective**: Real-time fraud detection under 50 ms p99 latency without PII exposure.

## Performance Metrics (Gate M2 Holdout)
- **PR-AUC**: **0.9944** (Target: ≥ 0.80, Rule Baseline: 0.0390)
- **ROC-AUC**: **0.9999**
- **Recall @ FPR ≤ 1%**: **0.9994** (Target: ≥ 0.80)
- **Decision Thresholds**:
  - `t_review`: `0.7` (Score ≥ 0.7 triggers REVIEW)
  - `t_block`: `0.75` (Score ≥ 0.75 triggers BLOCK)

## Confusion Matrix on Holdout
| Actual / Predicted | ALLOW | REVIEW | BLOCK | Total |
|---|---|---|---|---|
| **Fraud (Positive)** | 1 | 1 | 1598 | 1600 |
| **Legit (Negative)** | 101894 | 0 | 79 | 101973 |

## Features Used (Decision-Time Only)
1. `type_TRANSFER`, `type_CASH_OUT`, `type_PAYMENT`, `type_CASH_IN`, `type_DEBIT`
2. `log_amount`: log1p(amount)
3. `amount_to_balance`: amount / (oldbalanceOrg + 1)
4. `drains_account`: amount >= oldbalanceOrg
5. `payee_is_merchant`: PaySim nameDest prefix 'M'
6. `payee_prior_inbound`: bucketed historical frequency
7. `payee_balance_before_zero`: mule-account indicator
8. `hour_of_day`: simulation step % 24

*Notice: Post-transaction balances (`newbalanceOrig`, `newbalanceDest`) and `isFlaggedFraud`
are strictly excluded to avoid target leakage.*

## Ethical Considerations & Limitations
- **Synthetic Data**: Trained on PaySim synthetic mobile money transactions.
- **Demographics**: PaySim contains no user demographics. Protection for vulnerable/elderly
  users is achieved architecturally through non-invasive explanation prompts and deterministic
  reason codes.

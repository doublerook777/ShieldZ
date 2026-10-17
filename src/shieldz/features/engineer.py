"""Raw decision-time inputs -> model features.

One code path for training and serving: both call `_compute`, which works on numpy arrays.
Serving passes arrays of length 1. Only decision-time columns are used. PaySim's
`newbalanceOrig` / `newbalanceDest` are post-transaction and must never appear here (ADR D12).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from shieldz.contracts import FEATURE_ORDER, FeatureInput, FeatureVector, TxType
from shieldz.features.history import HistoryStore, bucket_prior_inbound

# Columns engineer_frame expects (training supplies payee_prior_inbound as a chronological count)
FRAME_INPUT_COLUMNS = (
    "tx_type",
    "amount",
    "payer_balance_before",
    "payee_balance_before",  # NaN = unknown
    "payee_is_merchant",
    "hour_of_day",
    "payee_prior_inbound",  # raw count, bucketed here
)


def _compute(tx_type, amount, payer_balance, payee_balance, merchant, hour, prior_count) -> dict:
    tx_type = np.asarray(tx_type, dtype=object)
    amount = np.asarray(amount, dtype=np.float64)
    payer_balance = np.asarray(payer_balance, dtype=np.float64)
    payee_balance = np.asarray(payee_balance, dtype=np.float64)  # NaN = unknown
    out = {f"type_{t.value}": (tx_type == t.value).astype(np.int64) for t in TxType}
    out["log_amount"] = np.log1p(amount)
    out["amount_to_balance"] = amount / (payer_balance + 1.0)
    out["drains_account"] = ((amount >= payer_balance) & (amount > 0)).astype(np.int64)
    out["payee_is_merchant"] = np.asarray(merchant).astype(np.int64)
    out["payee_prior_inbound"] = bucket_prior_inbound(prior_count)
    out["payee_balance_before_zero"] = (payee_balance == 0).astype(np.int64)  # NaN == 0 is False
    out["hour_of_day"] = np.asarray(hour).astype(np.int64)
    return {name: out[name] for name in FEATURE_ORDER}


def engineer(inp: FeatureInput, history: HistoryStore) -> FeatureVector:
    """Serving: one request. Reads the history store; the caller records the payment after."""
    unknown = np.nan if inp.payee_balance_before is None else inp.payee_balance_before
    cols = _compute(
        [inp.tx_type.value],
        [inp.amount],
        [inp.payer_balance_before],
        [unknown],
        [inp.payee_is_merchant],
        [inp.hour_of_day],
        [history.count(inp.payee_token)],
    )
    scalars = {k: v[0].item() for k, v in cols.items()}
    return FeatureVector(**scalars)


def engineer_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Training / batch: a DataFrame with FRAME_INPUT_COLUMNS -> a frame in FEATURE_ORDER."""
    cols = _compute(*(df[c].to_numpy() for c in FRAME_INPUT_COLUMNS))
    return pd.DataFrame(cols, index=df.index)

"""Parity tests for XGBoost model predictions and TreeSHAP reason codes (Gate M2)."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from shieldz.config import ROOT, model_dir
from shieldz.contracts import FEATURE_ORDER, FeatureVector, ReasonCode
from shieldz.model.engine import XGBoostEngine

GOLDEN_PRED = ROOT / "tests" / "golden" / "predictions_v1.csv"


@pytest.mark.skipif(not (model_dir() / "model.json").exists(), reason="Trained model not found")
def test_prediction_parity():
    if not GOLDEN_PRED.exists():
        pytest.skip("Golden predictions fixture not found")

    engine = XGBoostEngine.load(model_dir())
    df = pd.read_csv(GOLDEN_PRED)

    for i in range(min(100, len(df))):
        row = df.iloc[i]
        fv = FeatureVector(**{col: row[col] for col in FEATURE_ORDER})

        score = engine.score(fv)
        reasons = engine.reasons(fv)

        expected_score = float(row["expected_score"])
        assert score == pytest.approx(expected_score, abs=1e-4)

        if pd.notna(row["expected_reason_codes"]) and row["expected_reason_codes"]:
            expected_codes = row["expected_reason_codes"].split(";")
            actual_codes = [c.value for c, _ in reasons]
            assert actual_codes == expected_codes


@pytest.mark.skipif(not (model_dir() / "model.json").exists(), reason="Trained model not found")
def test_reason_codes_property_and_determinism():
    engine = XGBoostEngine.load(model_dir())

    # Generate synthetic feature vectors
    rng = np.random.default_rng(20261017)
    valid_enum_values = set(ReasonCode.__members__.values())

    for _ in range(200):
        dummy_data = {
            "type_TRANSFER": int(rng.choice([0, 1])),
            "type_CASH_OUT": int(rng.choice([0, 1])),
            "type_PAYMENT": 0,
            "type_CASH_IN": 0,
            "type_DEBIT": 0,
            "log_amount": float(rng.uniform(2.0, 14.0)),
            "amount_to_balance": float(rng.uniform(0.01, 1.5)),
            "drains_account": int(rng.choice([0, 1])),
            "payee_is_merchant": int(rng.choice([0, 1])),
            "payee_prior_inbound": int(rng.choice([0, 1, 2])),
            "payee_balance_before_zero": int(rng.choice([0, 1])),
            "hour_of_day": int(rng.integers(0, 24)),
        }
        fv = FeatureVector(**dummy_data)

        # 1. Determinism
        r1 = engine.reasons(fv)
        r2 = engine.reasons(fv)
        assert r1 == r2

        # 2. Closed enum property
        for code, level in r1:
            assert code in valid_enum_values

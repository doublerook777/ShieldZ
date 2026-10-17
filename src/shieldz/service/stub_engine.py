"""Rule-based stand-in for the trained model, so the service can be built and gated before M2.

Same `Engine` protocol as `XGBoostEngine`; swap with SHIELDZ_ENGINE=xgboost.
"""

from __future__ import annotations

import math

from shieldz.contracts import FeatureVector, Level, ReasonCode

REVIEW_MIN_AMOUNT = 5_000  # a new payee only matters once real money is involved


class StubEngine:
    name = "stub-rule"
    version = "stub-0"

    def score(self, features: FeatureVector) -> float:
        """Three bands, matching the default thresholds (review 0.5, block 0.9)."""
        risky = features.type_TRANSFER or features.type_CASH_OUT
        if risky and features.amount_to_balance >= 0.9:
            return 0.95
        if features.payee_prior_inbound == 0 and features.log_amount >= math.log1p(
            REVIEW_MIN_AMOUNT
        ):
            return 0.6
        return 0.02

    def reasons(self, features: FeatureVector) -> list[tuple[ReasonCode, Level]]:
        out: list[tuple[ReasonCode, Level]] = []
        if features.amount_to_balance >= 0.9:
            out.append((ReasonCode.AMOUNT_HIGH_VS_BALANCE, Level.HIGH))
        if features.drains_account:
            out.append((ReasonCode.ACCOUNT_DRAIN, Level.HIGH))
        if features.payee_prior_inbound == 0:
            out.append((ReasonCode.NEW_RECIPIENT, Level.MEDIUM))
        if features.type_TRANSFER or features.type_CASH_OUT:
            out.append((ReasonCode.RISKY_TRANSFER_TYPE, Level.MEDIUM))
        return out[:3]

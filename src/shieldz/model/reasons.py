"""Map model feature contributions (TreeSHAP) to closed ReasonCode and Level enums.

Raw feature values, names, and exact numbers are discarded; only the closed enum codes
and discrete levels (LOW/MEDIUM/HIGH) are returned (ARCHITECTURE §4).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from shieldz.contracts import FEATURE_ORDER, FeatureVector, Level, ReasonCode

MIN_CONTRIB: float = 0.1  # Minimum positive log-odds contribution required

# Mapping from feature column name to ReasonCode enum
FEATURE_TO_REASON: dict[str, ReasonCode] = {
    "amount_to_balance": ReasonCode.AMOUNT_HIGH_VS_BALANCE,
    "drains_account": ReasonCode.ACCOUNT_DRAIN,
    "payee_prior_inbound": ReasonCode.NEW_RECIPIENT,
    "type_TRANSFER": ReasonCode.RISKY_TRANSFER_TYPE,
    "type_CASH_OUT": ReasonCode.RISKY_TRANSFER_TYPE,
    "payee_balance_before_zero": ReasonCode.MULE_ACCOUNT_PATTERN,
    "log_amount": ReasonCode.LARGE_AMOUNT,
    "hour_of_day": ReasonCode.UNUSUAL_TIME,
}

_LEVEL_ORDER = {Level.LOW: 1, Level.MEDIUM: 2, Level.HIGH: 3}


def compute_level(code: ReasonCode, fv: FeatureVector) -> Level:
    """Assign discrete risk level from fixed thresholds on the feature value."""
    if code == ReasonCode.AMOUNT_HIGH_VS_BALANCE:
        if fv.amount_to_balance >= 0.9:
            return Level.HIGH
        if fv.amount_to_balance >= 0.5:
            return Level.MEDIUM
        return Level.LOW

    if code == ReasonCode.ACCOUNT_DRAIN:
        return Level.HIGH if fv.drains_account == 1 else Level.MEDIUM

    if code == ReasonCode.NEW_RECIPIENT:
        if fv.payee_prior_inbound == 0:
            return Level.HIGH
        if fv.payee_prior_inbound == 1:
            return Level.MEDIUM
        return Level.LOW

    if code == ReasonCode.RISKY_TRANSFER_TYPE:
        if fv.type_TRANSFER == 1 or fv.type_CASH_OUT == 1:
            return Level.HIGH
        return Level.LOW

    if code == ReasonCode.MULE_ACCOUNT_PATTERN:
        return Level.HIGH if fv.payee_balance_before_zero == 1 else Level.LOW

    if code == ReasonCode.LARGE_AMOUNT:
        if fv.log_amount >= 12.0:
            return Level.HIGH
        if fv.log_amount >= 9.0:
            return Level.MEDIUM
        return Level.LOW

    if code == ReasonCode.UNUSUAL_TIME:
        if fv.hour_of_day < 6 or fv.hour_of_day > 22:
            return Level.HIGH
        if fv.hour_of_day < 8 or fv.hour_of_day > 20:
            return Level.MEDIUM
        return Level.LOW

    return Level.LOW


def extract_reasons_from_contribs(
    features: FeatureVector,
    contribs: Sequence[float],
    min_contrib: float = MIN_CONTRIB,
    max_reasons: int = 3,
) -> list[tuple[ReasonCode, Level]]:
    """Convert raw TreeSHAP feature contributions into top (ReasonCode, Level) pairs.

    Args:
        features: FeatureVector of the transaction.
        contribs: List/array of SHAP log-odds contributions aligned with FEATURE_ORDER.
                  (If len(contribs) == len(FEATURE_ORDER) + 1, the last element is the bias).
        min_contrib: Minimum positive contribution threshold.
        max_reasons: Maximum number of reason codes to return (default 3).

    Returns:
        List of up to max_reasons (ReasonCode, Level) tuples, deterministic and sorted
        by contribution descending.
    """
    n_features = len(FEATURE_ORDER)
    feature_contribs = np.asarray(contribs[:n_features], dtype=np.float64)

    # Collect candidates with positive contributions >= min_contrib
    candidates: list[tuple[float, ReasonCode, Level]] = []
    seen_codes: dict[ReasonCode, float] = {}

    # Sort indices by contribution descending, breaking ties by feature name for determinism
    order = sorted(
        range(n_features),
        key=lambda i: (-feature_contribs[i], FEATURE_ORDER[i]),
    )

    for i in order:
        val = feature_contribs[i]
        if val < min_contrib:
            continue
        feat_name = FEATURE_ORDER[i]
        code = FEATURE_TO_REASON.get(feat_name, ReasonCode.OTHER_PATTERN)
        level = compute_level(code, features)

        if code not in seen_codes:
            seen_codes[code] = val
            candidates.append((val, code, level))

    if not candidates:
        return [(ReasonCode.OTHER_PATTERN, Level.LOW)]

    # Take top max_reasons
    return [(code, level) for _, code, level in candidates[:max_reasons]]

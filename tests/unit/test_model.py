import numpy as np
import pandas as pd

from shieldz.contracts import FEATURE_ORDER, FeatureVector, Level, ReasonCode
from shieldz.model.data import PAYSIM_USE_COLS, get_peak_rss_mb, prepare_features, time_based_split
from shieldz.model.reasons import (
    compute_level,
    extract_reasons_from_contribs,
)


def make_dummy_feature_vector(**kwargs) -> FeatureVector:
    base = {
        "type_TRANSFER": 1,
        "type_CASH_OUT": 0,
        "type_PAYMENT": 0,
        "type_CASH_IN": 0,
        "type_DEBIT": 0,
        "log_amount": 10.5,
        "amount_to_balance": 0.95,
        "drains_account": 1,
        "payee_is_merchant": 0,
        "payee_prior_inbound": 0,
        "payee_balance_before_zero": 1,
        "hour_of_day": 3,
    }
    base.update(kwargs)
    return FeatureVector(**base)


def test_no_banned_columns_in_loader():
    banned = ("newbalance", "new_balance", "isflaggedfraud")
    for col in PAYSIM_USE_COLS:
        assert not any(b in col.lower() for b in banned), f"Banned column found: {col}"


def test_prepare_features_produces_feature_order():
    raw_data = {
        "step": [1, 24],
        "type": ["TRANSFER", "PAYMENT"],
        "amount": [50000.0, 100.0],
        "nameOrig": ["C12345", "C67890"],
        "oldbalanceOrg": [50000.0, 2000.0],
        "nameDest": ["C98765", "M12345"],
        "oldbalanceDest": [0.0, 0.0],
        "isFraud": [1, 0],
    }
    df = pd.DataFrame(raw_data)
    X, y, step = prepare_features(df)

    assert list(X.columns) == list(FEATURE_ORDER)
    assert len(y) == 2
    assert len(step) == 2
    assert X["drains_account"].iloc[0] == 1
    assert X["payee_is_merchant"].iloc[1] == 1
    assert X["payee_balance_before_zero"].iloc[0] == 1
    # Merchant oldbalanceDest is 0 but balance is unknown -> payee_balance_before_zero should be 0
    assert X["payee_balance_before_zero"].iloc[1] == 0


def test_time_based_split():
    df = pd.DataFrame({"step": [10, 50, 100, 500, 600, 650, 700]})
    X = pd.DataFrame(np.zeros((7, len(FEATURE_ORDER))), columns=FEATURE_ORDER)
    y = pd.Series([0, 0, 1, 0, 1, 1, 0])
    step = df["step"]

    X_train, y_train, X_test, y_test = time_based_split(X, y, step, split_step=600)
    assert len(X_train) == 5
    assert len(X_test) == 2
    assert (step.iloc[:5] <= 600).all()
    assert (step.iloc[5:] > 600).all()


def test_reason_codes_are_in_enum():
    fv = make_dummy_feature_vector()
    contribs = [0.5] * len(FEATURE_ORDER)

    reasons = extract_reasons_from_contribs(fv, contribs)
    assert len(reasons) <= 3
    for code, level in reasons:
        assert isinstance(code, ReasonCode)
        assert isinstance(level, Level)


def test_reasons_determinism():
    fv = make_dummy_feature_vector()
    contribs = [0.2, 0.4, -0.1, 0.0, 0.0, 0.8, 1.2, 0.5, 0.0, 0.3, 0.7, 0.1]

    first = extract_reasons_from_contribs(fv, contribs)
    for _ in range(100):
        repeat = extract_reasons_from_contribs(fv, contribs)
        assert repeat == first


def test_reasons_fallback_when_below_min_contrib():
    fv = make_dummy_feature_vector()
    contribs = [0.01] * len(FEATURE_ORDER)

    reasons = extract_reasons_from_contribs(fv, contribs, min_contrib=0.1)
    assert reasons == [(ReasonCode.OTHER_PATTERN, Level.LOW)]


def test_compute_levels():
    fv_high = make_dummy_feature_vector(amount_to_balance=0.95, drains_account=1, hour_of_day=2)
    assert compute_level(ReasonCode.AMOUNT_HIGH_VS_BALANCE, fv_high) == Level.HIGH
    assert compute_level(ReasonCode.ACCOUNT_DRAIN, fv_high) == Level.HIGH
    assert compute_level(ReasonCode.UNUSUAL_TIME, fv_high) == Level.HIGH

    fv_med = make_dummy_feature_vector(amount_to_balance=0.6, hour_of_day=7)
    assert compute_level(ReasonCode.AMOUNT_HIGH_VS_BALANCE, fv_med) == Level.MEDIUM
    assert compute_level(ReasonCode.UNUSUAL_TIME, fv_med) == Level.MEDIUM


def test_peak_rss_non_negative():
    rss = get_peak_rss_mb()
    assert isinstance(rss, float)
    assert rss >= 0.0

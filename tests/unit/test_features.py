from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from shieldz.contracts import FEATURE_ORDER, FeatureInput, Language
from shieldz.features import HistoryStore, bucket_prior_inbound, engineer, engineer_frame
from shieldz.features.engineer import FRAME_INPUT_COLUMNS
from shieldz.features.history import DEMO_SEED
from shieldz.privacy import Tokenizer

GOLDEN = Path(__file__).resolve().parents[1] / "golden" / "features_v1.csv"


def make_input(**over):
    base = dict(
        tx_type="TRANSFER",
        amount=1000.0,
        payer_balance_before=50000.0,
        payee_balance_before=None,
        payee_is_merchant=False,
        hour_of_day=14,
        payee_token="t" * 32,
        payer_token="p" * 32,
        language=Language.EN,
    )
    return FeatureInput(**{**base, **over})


def test_account_drain():
    fv = engineer(make_input(amount=48300.0, payer_balance_before=48300.0), HistoryStore())
    assert fv.drains_account == 1
    assert fv.amount_to_balance == pytest.approx(48300 / 48301)


def test_partial_spend_is_not_a_drain():
    fv = engineer(make_input(amount=100.0, payer_balance_before=50000.0), HistoryStore())
    assert fv.drains_account == 0
    assert fv.amount_to_balance < 0.01


def test_mule_pattern_needs_a_known_zero_balance():
    store = HistoryStore()
    assert engineer(make_input(payee_balance_before=0.0), store).payee_balance_before_zero == 1
    assert engineer(make_input(payee_balance_before=None), store).payee_balance_before_zero == 0
    assert engineer(make_input(payee_balance_before=12.0), store).payee_balance_before_zero == 0


def test_new_recipient_and_history():
    store = HistoryStore()
    inp = make_input()
    assert engineer(inp, store).payee_prior_inbound == 0
    store.record(inp.payee_token)
    assert engineer(inp, store).payee_prior_inbound == 1
    for _ in range(3):
        store.record(inp.payee_token)
    assert engineer(inp, store).payee_prior_inbound == 2


def test_engineer_does_not_record():
    store = HistoryStore()
    engineer(make_input(), store)
    assert len(store) == 0


@pytest.mark.parametrize("count,bucket", [(0, 0), (1, 1), (3, 1), (4, 2), (5000, 2)])
def test_bucket_edges(count, bucket):
    assert int(bucket_prior_inbound(count)) == bucket


def test_type_one_hot():
    fv = engineer(make_input(tx_type="CASH_OUT"), HistoryStore())
    assert (fv.type_CASH_OUT, fv.type_TRANSFER, fv.type_PAYMENT) == (1, 0, 0)


def test_no_post_transaction_columns():
    banned = ("newbalance", "new_balance", "after", "post", "isflaggedfraud")
    for name in FEATURE_ORDER + FRAME_INPUT_COLUMNS:
        assert not any(b in name.lower() for b in banned), name


def test_feature_list_is_the_documented_one():
    assert FEATURE_ORDER == (
        "type_TRANSFER",
        "type_CASH_OUT",
        "type_PAYMENT",
        "type_CASH_IN",
        "type_DEBIT",
        "log_amount",
        "amount_to_balance",
        "drains_account",
        "payee_is_merchant",
        "payee_prior_inbound",
        "payee_balance_before_zero",
        "hour_of_day",
    )


def test_cold_start_with_seed_puts_demo_payee_in_top_bucket():
    tok = Tokenizer(b"x" * 32)
    store = HistoryStore()
    store.seed_from_csv(tok, DEMO_SEED)
    bill = make_input(payee_token=tok.token("demo electricity board"))
    assert engineer(bill, store).payee_prior_inbound == 2
    stranger = make_input(payee_token=tok.token("9001 2222 3333"))
    assert engineer(stranger, store).payee_prior_inbound == 0


def test_history_snapshot_roundtrip(tmp_path):
    store = HistoryStore()
    store.seed_counts([("a" * 32, 7), ("b" * 32, 1)])
    store.save(tmp_path / "h.sqlite")
    fresh = HistoryStore()
    fresh.load(tmp_path / "h.sqlite")
    assert (fresh.count("a" * 32), fresh.count("b" * 32)) == (7, 1)


def test_serving_row_matches_batch_row():
    """The serving path and the training path must give the same numbers."""
    gold = pd.read_csv(GOLDEN)
    store = HistoryStore()
    for i in range(0, len(gold), 17):
        row = gold.iloc[i]
        token = f"{i:032d}"
        store.seed_counts([(token, int(row["payee_prior_inbound"]))])
        known = not np.isnan(row["payee_balance_before"])
        inp = make_input(
            tx_type=row["tx_type"],
            amount=row["amount"],
            payer_balance_before=row["payer_balance_before"],
            payee_balance_before=row["payee_balance_before"] if known else None,
            payee_is_merchant=bool(row["payee_is_merchant"]),
            hour_of_day=int(row["hour_of_day"]),
            payee_token=token,
        )
        fv = engineer(inp, store).model_dump()
        for name in FEATURE_ORDER:
            assert fv[name] == pytest.approx(row[f"expected_{name}"], rel=1e-9), (i, name)


def test_golden_features_v1():
    """Parity: same inputs give the same features on a laptop and on LinuxONE."""
    gold = pd.read_csv(GOLDEN)
    assert len(gold) == 200
    got = engineer_frame(gold[list(FRAME_INPUT_COLUMNS)])
    for name in FEATURE_ORDER:
        np.testing.assert_allclose(
            got[name].to_numpy(), gold[f"expected_{name}"].to_numpy(), rtol=1e-9, atol=0
        )

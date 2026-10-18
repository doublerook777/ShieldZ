"""M3 gate: API contract, 422 without echo, log PII test, outbox row per request, clean start."""

from __future__ import annotations

import io
import json
import logging

import pytest
from fastapi.testclient import TestClient

from shieldz.contracts import DecisionKind, Explanation, ExplanationSource, Language
from shieldz.features.history import SqliteHistoryStore
from shieldz.outbox.queue import Outbox
from shieldz.privacy.redact_log import ALLOWED_FIELDS, setup_logging
from shieldz.privacy.tokenize import Tokenizer
from shieldz.service.app import create_app
from shieldz.service.decide import DEFAULT_THRESHOLDS, Thresholds, decide, load_thresholds
from shieldz.service.pipeline import Pipeline, build_history
from shieldz.service.stub_engine import StubEngine

PEPPER = b"\x01" * 32


@pytest.fixture
def env(tmp_path):
    log_file = tmp_path / "logs" / "app.jsonl"
    stream = io.StringIO()
    setup_logging(log_file, stream)
    tokenizer = Tokenizer(PEPPER)
    pipeline = Pipeline(
        engine=StubEngine(),
        thresholds=DEFAULT_THRESHOLDS,
        tokenizer=tokenizer,
        history=build_history(tokenizer),
        outbox=Outbox(tmp_path / "outbox.sqlite"),
    )
    with TestClient(create_app(pipeline)) as client:
        yield client, pipeline, log_file, stream
    logging.getLogger("shieldz").handlers.clear()


def payment(**over):
    body = {
        "payer_name": "Savitri Devi Kulkarni",
        "payer_phone": "+919876501234",
        "payer_account": "ACC-7731-0042",
        "payee_name": "Quick Cash Traders",
        "payee_account": "UPI-quickcash@okbank",
        "memo": "CANARY-ab12cd pay urgently",
        "family_contact": "Ramesh Kulkarni",
        "tx_type": "TRANSFER",
        "amount": 48250.37,
        "payer_balance_before": 48300.0,
        "payee_balance_before": 0,
        "timestamp": "2026-10-17T03:15:00+05:30",
        "language": "HI",
    }
    return {**body, **over}


def test_scam_like_payment_is_blocked_with_reasons(env):
    client, *_ = env
    r = client.post("/v1/score", json=payment())
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "BLOCK" and body["risk_level"] == "HIGH"
    assert {x["code"] for x in body["reason_codes"]} >= {"AMOUNT_HIGH_VS_BALANCE"}
    assert len(body["reason_codes"]) <= 3
    assert set(body) == {
        "decision_id",
        "decision",
        "risk_level",
        "reason_codes",
        "model_version",
        "server_ms",
    }


def test_clean_start_bill_payment_is_allowed(env):
    """Demo scenario (b): a normal payment to a seeded utility."""
    client, *_ = env
    r = client.post(
        "/v1/score",
        json=payment(
            tx_type="PAYMENT",
            payee_account="DEMO-ELECTRICITY-BOARD",
            amount=1840.0,
            payer_balance_before=62000.0,
            payee_is_merchant=True,
            timestamp="2026-10-17T11:00:00+05:30",
        ),
    )
    assert r.json()["decision"] == "ALLOW"
    assert r.json()["reason_codes"] == []


def test_response_has_no_pii_and_no_score(env):
    client, *_ = env
    text = client.post("/v1/score", json=payment()).text
    for secret in ("Savitri", "9876501234", "ACC-7731", "quickcash", "CANARY", "48250", "Ramesh"):
        assert secret not in text
    assert "score" not in text and "probability" not in text


def test_invalid_request_is_422_without_echo(env):
    client, *_ = env
    bad = payment(amount="not-a-number", tx_type="SECRET-TYPE-VALUE", payer_account="x")
    bad["surprise_field"] = "LEAKY-VALUE-123"
    r = client.post("/v1/score", json=bad)
    assert r.status_code == 422
    for secret in ("not-a-number", "SECRET-TYPE-VALUE", "LEAKY-VALUE-123", "Savitri", "9876501234"):
        assert secret not in r.text
    assert all(set(e) == {"loc", "type"} for e in r.json()["detail"])


def test_malformed_json_is_422_without_echo(env):
    client, *_ = env
    r = client.post(
        "/v1/score",
        content=b'{"payer_name": "Savitri Kulkarni", ',
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 422 and "Savitri" not in r.text


def test_healthz_reports_platform_and_engine(env):
    client, *_ = env
    body = client.get("/healthz").json()
    assert body["status"] == "ok" and body["engine"] == "stub-rule" and body["platform"]


def test_log_pii_test_50_requests(env):
    """Gate: 50 requests with distinctive PII -> captured logs contain none of it."""
    client, _, log_file, stream = env
    secrets = []
    for i in range(50):
        name, phone = f"Zubin Qureshi{i}", f"+9198{i:08d}"
        acct, memo = f"AC-{9000 + i}-XQ", f"CANARY-{i:04x}ff"
        secrets += [name, phone, acct, memo, f"{1000 + i}.37"]
        r = client.post(
            "/v1/score",
            json=payment(
                payer_name=name,
                payer_phone=phone,
                payer_account=acct,
                memo=memo,
                amount=1000 + i + 0.37,
                payer_balance_before=1000 + i + 0.37,
            ),
        )
        assert r.status_code == 200
    # also provoke a 422 and a 404
    client.post("/v1/score", json=payment(payer_name="", memo="CANARY-bad"))
    client.get("/v1/explanations/" + "0" * 32)
    logged = log_file.read_text() + stream.getvalue()
    assert log_file.read_text().count('"event":"decision"') == 50
    assert len(log_file.read_text().splitlines()) == len(stream.getvalue().splitlines())
    for s in secrets + ["CANARY-bad", "Zubin", "Savitri"]:
        assert s not in logged
    for line in logged.splitlines():
        assert set(json.loads(line)) <= ALLOWED_FIELDS | {"ts"}


def test_logger_drops_unknown_fields_and_free_text(env):
    from shieldz.privacy.redact_log import log_event

    _, _, log_file, _ = env
    log_event("probe", payer_name="Savitri Devi", memo="CANARY-x", status="ok")
    line = json.loads(log_file.read_text().splitlines()[-1])
    assert line["event"] == "probe" and line["status"] == "ok"
    assert "payer_name" not in line and "memo" not in line


def test_each_request_writes_one_outbox_row(env):
    client, pipeline, *_ = env
    client.post("/v1/score", json=payment())
    client.post("/v1/score", json=payment(tx_type="PAYMENT", amount=10, payer_balance_before=5000))
    client.post("/v1/score", json=payment(amount=-1))  # rejected: no row
    assert pipeline.outbox.count() == 2
    assert pipeline.outbox.count("pending") == 1 and pipeline.outbox.count("skipped") == 1


def test_outbox_holds_codes_only(env):
    client, pipeline, *_ = env
    client.post("/v1/score", json=payment())
    job = pipeline.outbox.claim_next()
    assert job is not None and job.decision == DecisionKind.BLOCK and job.language == Language.HI
    assert pipeline.outbox.claim_next() is None
    raw = pipeline.outbox.path.read_bytes()
    for secret in (b"Savitri", b"9876501234", b"ACC-7731", b"CANARY", b"48250"):
        assert secret not in raw


def test_explanation_endpoint_roundtrip(env):
    client, pipeline, *_ = env
    decision_id = client.post("/v1/score", json=payment()).json()["decision_id"]
    assert client.get(f"/v1/explanations/{decision_id}").status_code == 404
    pipeline.outbox.put_explanation(
        Explanation(
            decision_id=decision_id,
            text="Please pause and call your bank.",
            source=ExplanationSource.TEMPLATE,
            language=Language.HI,
            ts="2026-10-17T10:00:00.000Z",
        )
    )
    got = client.get(f"/v1/explanations/{decision_id}")
    assert got.status_code == 200 and got.json()["source"] == "template"
    assert client.get("/v1/explanations/not-a-valid-id").status_code == 422


def test_outbox_failure_does_not_fail_the_decision(env):
    client, pipeline, *_ = env

    class Broken:
        def enqueue(self, job):
            import sqlite3

            raise sqlite3.OperationalError("disk I/O error")

    pipeline.outbox = Broken()
    assert client.post("/v1/score", json=payment()).status_code == 200


def test_payee_becomes_known_after_first_payment(env):
    client, *_ = env
    kw = {"payee_account": "FRESH-PAYEE-001", "tx_type": "PAYMENT", "payer_balance_before": 9e5}
    first = client.post("/v1/score", json=payment(**kw))
    assert first.status_code == 200
    assert (
        client.app.state.pipeline.history.count(
            client.app.state.pipeline.tokenizer.token("FRESH-PAYEE-001")
        )
        == 1
    )


def test_decide_bands_and_threshold_validation(tmp_path):
    t = Thresholds(t_review=0.3, t_block=0.8)
    assert decide(0.1, t)[0] == DecisionKind.ALLOW
    assert decide(0.3, t)[0] == DecisionKind.REVIEW
    assert decide(0.8, t)[0] == DecisionKind.BLOCK
    with pytest.raises(ValueError):
        Thresholds(t_review=0.9, t_block=0.5)
    assert load_thresholds(tmp_path / "missing.json") == DEFAULT_THRESHOLDS
    f = tmp_path / "thresholds.json"
    f.write_text(json.dumps({"t_review": 0.2, "t_block": 0.7}))
    assert load_thresholds(f) == Thresholds(0.2, 0.7)


def test_sqlite_history_survives_restart_without_double_seeding(tmp_path):
    tk = Tokenizer(PEPPER)
    path = tmp_path / "history.sqlite"
    first = build_history(tk, path)
    first.record(tk.token("DEMO-ELECTRICITY-BOARD"))
    second = build_history(tk, path)  # a restart (or a second worker)
    token = tk.token("DEMO-ELECTRICITY-BOARD")
    assert first.count(token) == second.count(token) == 5201
    assert isinstance(second, SqliteHistoryStore)


def test_audit_chain_and_signed_checkpoints_cover_every_decision(tmp_path):
    from shieldz.audit import AuditChain, CheckpointSigner, verify_audit_trail

    chain_file, cps = tmp_path / "audit" / "chain.jsonl", tmp_path / "audit" / "checkpoints.jsonl"
    priv, pub = tmp_path / "keys" / "k.pem", tmp_path / "keys" / "k_pub.pem"
    chain = AuditChain(chain_file)
    tokenizer = Tokenizer(PEPPER)
    pipeline = Pipeline(
        engine=StubEngine(),
        thresholds=DEFAULT_THRESHOLDS,
        tokenizer=tokenizer,
        history=build_history(tokenizer),
        outbox=Outbox(tmp_path / "outbox.sqlite"),
        audit_append=lambda d: chain.append(
            d.decision_id, d.decision, d.risk_level, d.reason_codes, d.model_version
        ),
        signer=CheckpointSigner(chain, cps, priv, pub),
    )
    with TestClient(create_app(pipeline)) as client:
        for i in range(12):
            body = payment(amount=100 + i, payer_balance_before=100 + i) if i % 2 else payment()
            assert client.post("/v1/score", json=body).status_code == 200
    raw = chain_file.read_text()
    assert len(raw.splitlines()) == 12
    for secret in ("Savitri", "9876501234", "ACC-7731", "CANARY", "48250"):
        assert secret not in raw
    ok, message, _ = verify_audit_trail(chain_file, cps, pub)
    assert ok, message
    assert "checkpoint" in message


def test_audit_failure_does_not_fail_the_decision(env):
    client, pipeline, *_ = env

    def broken(decision):
        raise OSError("disk full")

    pipeline.audit_append = broken
    assert client.post("/v1/score", json=payment()).status_code == 200


def test_demo_scenarios_get_their_expected_decisions(env):
    """The three scripted stories (Member 4) must come out right on the stub, too: A BLOCK, B ALLOW,
    C REVIEW. The real model has to pass the same check on the VM (M2 thresholds)."""
    import importlib.util
    import sys
    from pathlib import Path

    path = Path(__file__).parents[2] / "scripts" / "demo_scenarios.py"
    spec = importlib.util.spec_from_file_location("demo_scenarios", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["demo_scenarios"] = module  # dataclasses look their module up here
    spec.loader.exec_module(module)

    client, *_ = env
    for sc in module.SCENARIOS.values():
        body = client.post("/v1/score", json=sc.payment).json()
        assert body["decision"] == sc.expected_decision.value, sc.id
        assert body["risk_level"] == sc.expected_risk.value, sc.id


class LowScoreEngine(StubEngine):
    """Like the trained model on an ordinary payment: scores about 0.03 whatever the payee."""

    name, version = "low", "low-0"

    def score(self, features):
        return 0.03

    def reasons(self, features):
        return []


@pytest.fixture
def low_env(tmp_path):
    setup_logging(tmp_path / "logs" / "app.jsonl", io.StringIO())
    tokenizer = Tokenizer(PEPPER)
    pipeline = Pipeline(
        engine=LowScoreEngine(),
        thresholds=DEFAULT_THRESHOLDS,
        tokenizer=tokenizer,
        history=build_history(tokenizer),
        outbox=Outbox(tmp_path / "outbox.sqlite"),
    )
    with TestClient(create_app(pipeline)) as client:
        yield client, pipeline
    logging.getLogger("shieldz").handlers.clear()


def test_policy_holds_a_large_share_of_the_balance_sent_to_a_new_payee(low_env):
    """The model alone scores this 0.03-0.15 (a partial transfer, not a full drain): ALLOW."""
    client, pipeline = low_env
    body = payment(tx_type="TRANSFER", amount=245000.0, payer_balance_before=490000.0)
    first = client.post("/v1/score", json=body).json()
    assert first["decision"] == "REVIEW" and first["risk_level"] == "MEDIUM"
    assert [r["code"] for r in first["reason_codes"]] == ["NEW_RECIPIENT", "LARGE_AMOUNT"]
    assert pipeline.outbox.count("pending") == 1  # the explainer gets the job
    # the payee is known after one payment: the same request is now an ALLOW
    assert client.post("/v1/score", json=body).json()["decision"] == "ALLOW"


def test_policy_does_not_add_friction_to_ordinary_payments(low_env):
    """Paying a new merchant is normal: a clinic bill, a small transfer, a known payee."""
    client, _ = low_env
    clinic = payment(tx_type="PAYMENT", amount=8500.0, payer_balance_before=490000.0)
    assert client.post("/v1/score", json=clinic).json()["decision"] == "ALLOW"
    utility = payment(
        tx_type="TRANSFER", payee_account="DEMO-ELECTRICITY-BOARD", amount=245000.0,
        payer_balance_before=490000.0,
    )  # fmt: skip
    assert client.post("/v1/score", json=utility).json()["decision"] == "ALLOW"  # known payee
    small = payment(
        tx_type="TRANSFER", payee_account="NEW-SMALL-2", amount=900.0, payer_balance_before=1500.0
    )  # 60% of the balance, but only Rs 900
    assert client.post("/v1/score", json=small).json()["decision"] == "ALLOW"  # amount floor


def test_policy_can_be_switched_off_and_never_lowers_a_decision(tmp_path):
    from dataclasses import replace

    from shieldz.contracts import DecisionKind, FeatureVector
    from shieldz.service.decide import apply_policy

    off = replace(DEFAULT_THRESHOLDS, review_new_payee_ratio=None)
    f = {
        "type_TRANSFER": 1, "type_CASH_OUT": 0, "type_PAYMENT": 0, "type_CASH_IN": 0,
        "type_DEBIT": 0, "log_amount": 12.4, "amount_to_balance": 0.5, "drains_account": 0,
        "payee_is_merchant": 0, "payee_prior_inbound": 0, "payee_balance_before_zero": 1,
        "hour_of_day": 23,
    }  # fmt: skip
    vec = FeatureVector(**f)
    kind, risk, reasons = apply_policy(DecisionKind.ALLOW, vec, DEFAULT_THRESHOLDS)
    assert kind == DecisionKind.REVIEW and len(reasons) == 2
    assert apply_policy(DecisionKind.ALLOW, vec, off)[0] == DecisionKind.ALLOW
    assert apply_policy(DecisionKind.BLOCK, vec, DEFAULT_THRESHOLDS)[0] == DecisionKind.BLOCK
    assert apply_policy(DecisionKind.REVIEW, vec, DEFAULT_THRESHOLDS)[2] == []
    ordinary = FeatureVector(**{**f, "amount_to_balance": 0.017, "log_amount": 9.05})
    assert apply_policy(DecisionKind.ALLOW, ordinary, DEFAULT_THRESHOLDS)[0] == DecisionKind.ALLOW


def test_thresholds_file_can_tune_or_disable_the_policy(tmp_path):
    f = tmp_path / "thresholds.json"
    f.write_text(json.dumps({"t_review": 0.7, "t_block": 0.75, "review_new_payee_ratio": None}))
    assert load_thresholds(f).review_new_payee_ratio is None
    f.write_text(json.dumps({"t_review": 0.7, "t_block": 0.75}))
    loaded = load_thresholds(f)
    assert loaded.review_new_payee_ratio == 0.4 and loaded.review_new_payee_min_amount == 10_000.0
    f.write_text(json.dumps({"t_review": 0.7, "t_block": 0.75, "review_new_payee_ratio": 0.6}))
    assert load_thresholds(f).review_new_payee_ratio == 0.6

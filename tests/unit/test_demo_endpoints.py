"""M7 backend: audit verify and scorecard endpoints, static page, and the live Leak Audit replay."""

from __future__ import annotations

import json
import logging

import pytest
from fastapi.testclient import TestClient

from shieldz import config
from shieldz.audit import AuditChain, CheckpointSigner
from shieldz.leak_audit.canaries import generate_canaries
from shieldz.outbox.queue import Outbox
from shieldz.privacy.tokenize import Tokenizer
from shieldz.service import app as app_module
from shieldz.service.app import create_app
from shieldz.service.decide import DEFAULT_THRESHOLDS
from shieldz.service.live_replay import live_pipeline_fn, to_request
from shieldz.service.pipeline import Pipeline, build_history
from shieldz.service.stub_engine import StubEngine

PEPPER = b"\x02" * 32


@pytest.fixture
def audited(tmp_path, monkeypatch):
    monkeypatch.setenv("SHIELDZ_ARTIFACTS", str(tmp_path))
    monkeypatch.setenv("SHIELDZ_RESULTS", str(tmp_path / "results"))
    tokenizer = Tokenizer(PEPPER)
    chain = AuditChain(config.audit_chain_file())
    pipeline = Pipeline(
        engine=StubEngine(),
        thresholds=DEFAULT_THRESHOLDS,
        tokenizer=tokenizer,
        history=build_history(tokenizer),
        outbox=Outbox(tmp_path / "outbox.sqlite"),
        audit_append=lambda d: chain.append(
            d.decision_id, d.decision, d.risk_level, d.reason_codes, d.model_version
        ),
        signer=CheckpointSigner(
            chain,
            config.audit_checkpoints_file(),
            config.audit_private_key(),
            config.audit_public_key(),
        ),
    )
    with TestClient(create_app(pipeline)) as client:
        yield client, tmp_path


def body(**over):
    base = {
        "payer_name": "Savitri Devi Kulkarni",
        "payer_phone": "+919876501234",
        "payer_account": "ACC-7731-0042",
        "payee_name": "Quick Cash Traders",
        "payee_account": "UPI-quickcash@okbank",
        "tx_type": "TRANSFER",
        "amount": 48250.37,
        "payer_balance_before": 48250.37,
        "timestamp": "2026-10-17T03:15:00+05:30",
    }
    return base | over


def test_audit_verify_passes_then_detects_tampering(audited):
    client, tmp_path = audited
    for _ in range(5):
        assert client.post("/v1/score", json=body()).status_code == 200
    ok = client.get("/v1/audit/verify").json()
    assert ok["ok"] is True and ok["failure_seq"] is None

    chain_file = config.audit_chain_file()
    lines = chain_file.read_text().splitlines()
    entry = json.loads(lines[2])
    entry["decision"] = "ALLOW" if entry["decision"] != "ALLOW" else "BLOCK"
    lines[2] = json.dumps(entry)
    chain_file.write_text("\n".join(lines) + "\n")
    bad = client.get("/v1/audit/verify").json()
    assert bad["ok"] is False and bad["failure_seq"] == 2


def test_scorecard_endpoint_prefers_linuxone_and_drops_findings(audited):
    client, tmp_path = audited
    assert client.get("/v1/leak-scorecard").status_code == 404
    results = tmp_path / "results"
    results.mkdir()
    card = {"environment": "local", "status": "PASS", "leaks_exact": 0, "findings": ["SECRET"]}
    (results / "leak_scorecard_local.json").write_text(json.dumps(card))
    got = client.get("/v1/leak-scorecard").json()
    assert got["environment"] == "local" and "findings" not in got
    (results / "leak_scorecard_linuxone.json").write_text(json.dumps(card | {"environment": "z"}))
    assert client.get("/v1/leak-scorecard").json()["environment"] == "z"


def test_static_page_is_served_without_shadowing_the_api(tmp_path, monkeypatch):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<title>demo</title>")
    monkeypatch.setattr(app_module, "STATIC_DIR", static)
    monkeypatch.setenv("SHIELDZ_RESULTS", str(tmp_path / "none"))
    tokenizer = Tokenizer(PEPPER)
    pipeline = Pipeline(
        engine=StubEngine(),
        thresholds=DEFAULT_THRESHOLDS,
        tokenizer=tokenizer,
        history=build_history(tokenizer),
        outbox=Outbox(tmp_path / "outbox.sqlite"),
    )
    with TestClient(create_app(pipeline)) as client:
        page = client.get("/")
        assert "<title>demo</title>" in page.text
        assert page.headers["cache-control"] == "no-cache"
        assert client.get("/healthz").json()["status"] == "ok"
        assert client.get("/v1/leak-scorecard").status_code == 404  # an API route, not a file


def test_canaries_fit_the_real_contract():
    from shieldz.contracts import PaymentRequest

    for i, canary in enumerate(generate_canaries(n=30, seed=42)):
        PaymentRequest(**to_request(canary.to_payment_request_dict(), i))


def test_live_replay_fills_every_sink_with_zero_leaks(tmp_path, monkeypatch):
    from shieldz.leak_audit.replay import run_leak_audit

    monkeypatch.setenv("SHIELDZ_ARTIFACTS", str(tmp_path))
    runtime = config.runtime_dir()
    fn, close = live_pipeline_fn(runtime)
    try:
        card = run_leak_audit(runtime, pipeline_fn=fn, n_canaries=60, results_dir=tmp_path / "res")
    finally:
        close()
        logging.getLogger("shieldz").handlers.clear()
    assert card.status == "PASS" and card.leaks_exact == card.leaks_variant == 0
    for sink in ("app_log", "audit_chain", "prompt_journal", "outbox_sqlite", "history_sqlite"):
        assert card.bytes_per_sink[sink] > 0, f"{sink} was never written, so it proved nothing"


def test_ui_scenarios_match_the_cli_scenarios():
    """The UI keeps its own copy of the scenario data. It drifted once (balance 490,000 instead of
    485,000), which turned the scam from a full drain (BLOCK) into a REVIEW on screen."""
    import importlib.util
    import re
    import sys
    from pathlib import Path

    root = Path(__file__).parents[2]
    spec = importlib.util.spec_from_file_location(
        "demo_scenarios", root / "scripts/demo_scenarios.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["demo_scenarios"] = module
    spec.loader.exec_module(module)
    html = (root / "src/shieldz/service/static/index.html").read_text()

    def ui_value(block: str, key: str) -> str:
        return re.search(rf"\b{key}:\s*[\"']?([^\"',\n]+)", block).group(1).strip()

    for key, sc in module.SCENARIOS.items():
        start = html.index(f"{key}: {{", html.index("const SCENARIO_DATA"))
        block = html[start : html.index("}", start)]
        assert float(ui_value(block, "amount")) == sc.payment["amount"], key
        assert (
            float(ui_value(block, "payer_balance_before")) == sc.payment["payer_balance_before"]
        ), key
        assert ui_value(block, "tx_type") == sc.payment["tx_type"], key
        assert ui_value(block, "payee_account") == sc.payment["payee_account"], key

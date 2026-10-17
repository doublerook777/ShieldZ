"""Drive the real service from the Leak Audit: `python -m shieldz.leak_audit --live`.

The default replay targets a stand-in that only writes an app log, so five of six sinks stay empty
and "0 leaks" says little. This pushes every canary through the actual app (strip, features, engine,
history, audit chain, outbox), runs the explainer worker over the queue so the prompt journal fills
too, and returns the HTTP bodies the way a client would see them (decision plus explanation).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from shieldz import config
from shieldz.audit import AuditChain, CheckpointSigner
from shieldz.explainer.journal import PromptJournal
from shieldz.explainer.worker import Worker, load_generator
from shieldz.outbox.queue import Outbox
from shieldz.privacy.redact_log import setup_logging
from shieldz.privacy.tokenize import default_tokenizer
from shieldz.service.app import create_app
from shieldz.service.decide import load_thresholds
from shieldz.service.pipeline import Pipeline, build_history, load_engine

LANGUAGES = ("EN", "HI", "TA")


def to_request(canary: dict[str, Any], i: int) -> dict[str, Any]:
    """Fit a canary to the real `PaymentRequest`. The contract forbids extra fields, so the extra
    identifiers (UPI id, email) ride along in the free-text memo, which `strip()` must drop.
    Every third payment drains the account, so BLOCK, the outbox and the journal get exercised."""
    request = {
        k: v for k, v in canary.items() if k not in ("request_id", "upi_id", "email", "memo")
    }
    request["memo"] = f"{canary['memo']} {canary['upi_id']} {canary['email']}"
    request["family_contact"] = canary["payee_name"]
    request["timestamp"] = "2026-10-17T03:15:00+05:30"
    request["language"] = LANGUAGES[i % len(LANGUAGES)]
    request["payee_balance_before"] = 0
    if i % 3 == 0:
        request["payer_balance_before"] = request["amount"]
    return request


def live_pipeline_fn(runtime: Path) -> tuple[Callable[[dict[str, Any]], str], Callable[[], None]]:
    """Return (pipeline_fn, close). Sinks land under `runtime`, where `SinkRegistry` looks."""
    setup_logging(runtime / "logs" / "app.jsonl")
    tokenizer = default_tokenizer()
    chain = AuditChain(runtime / "audit" / "chain.jsonl")
    outbox = Outbox(runtime / "outbox.sqlite")
    pipeline = Pipeline(
        engine=load_engine(),
        thresholds=load_thresholds(),
        tokenizer=tokenizer,
        history=build_history(tokenizer, runtime / "history.sqlite"),
        outbox=outbox,
        audit_append=lambda d: chain.append(
            d.decision_id, d.decision, d.risk_level, d.reason_codes, d.model_version
        ),
        signer=CheckpointSigner(
            chain,
            runtime / "audit" / "checkpoints.jsonl",
            config.audit_private_key(),
            config.audit_public_key(),
        ),
    )
    worker = Worker(outbox, load_generator(), PromptJournal(runtime / "journal" / "prompts.jsonl"))
    client = TestClient(create_app(pipeline))
    client.__enter__()  # runs the lifespan: starts the checkpoint signer

    sent = 0

    def checkpoint() -> None:
        """Fold the WALs into the main files. Left alone they grow to megabytes of duplicate pages,
        and the scan (which runs before `close`) would read everything twice."""
        for name in ("history.sqlite", "outbox.sqlite"):
            with sqlite3.connect(runtime / name) as db:
                db.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    def replay(canary: dict[str, Any]) -> str:
        nonlocal sent
        sent += 1
        decision = client.post("/v1/score", json=to_request(canary, sent))
        if decision.status_code != 200:  # a rejected canary would make "0 leaks" meaningless
            raise RuntimeError(f"live replay request rejected with HTTP {decision.status_code}")
        worker.run_once()  # BLOCK/REVIEW jobs only; ALLOW is skipped by the outbox
        explanation = client.get(f"/v1/explanations/{decision.json()['decision_id']}")
        if sent % 100 == 0:
            checkpoint()
        return json.dumps([decision.text, explanation.text])

    def close() -> None:
        client.__exit__(None, None, None)
        logging.getLogger("shieldz").handlers.clear()

    return replay, close

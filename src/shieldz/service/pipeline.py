"""The decision path (ARCHITECTURE §3): validate -> strip -> engineer -> score -> decide -> reasons
-> audit -> outbox -> respond.

Everything after `strip()` sees tokens and numbers only (I1). Nothing here waits on the LLM (I3):
the outbox insert is the whole hand-off.
"""

from __future__ import annotations

import os
import sqlite3
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from shieldz import config
from shieldz.audit import AuditChain, CheckpointSigner
from shieldz.config import runtime_dir
from shieldz.contracts import (
    Decision,
    DecisionKind,
    Engine,
    ExplainJob,
    FeatureInput,
    Level,
    PaymentRequest,
    Reason,
    ReasonCode,
)
from shieldz.features.engineer import engineer
from shieldz.features.history import History, HistoryStore, SqliteHistoryStore
from shieldz.outbox.queue import Outbox
from shieldz.privacy.redact_log import log_event
from shieldz.privacy.strip import strip
from shieldz.privacy.tokenize import Tokenizer, default_tokenizer
from shieldz.service.decide import Thresholds, apply_policy, decide, load_thresholds
from shieldz.service.stub_engine import StubEngine

MAX_REASONS = 3
AuditAppend = Callable[[Decision], None]


def load_engine(name: str | None = None) -> Engine:
    """SHIELDZ_ENGINE=stub (default until M2 lands) or xgboost (`model.engine.XGBoostEngine`)."""
    name = name or os.environ.get("SHIELDZ_ENGINE", "stub")
    if name == "stub":
        return StubEngine()
    if name == "xgboost":
        from shieldz.config import model_dir
        from shieldz.model.engine import XGBoostEngine

        return XGBoostEngine.load(model_dir())
    raise ValueError(f"unknown engine {name!r}")


def build_history(tokenizer: Tokenizer, path: Path | None = None) -> History:
    """With a path: the SQLite store shared by all api workers, seeded once. Without: in memory."""
    history = SqliteHistoryStore(path) if path is not None else HistoryStore()
    history.seed_from_csv(tokenizer)
    return history


@dataclass
class Pipeline:
    engine: Engine
    thresholds: Thresholds
    tokenizer: Tokenizer
    history: History
    outbox: Outbox
    audit_append: AuditAppend | None = None
    signer: CheckpointSigner | None = None  # background checkpoint signing (never in the request)

    @classmethod
    def from_env(cls) -> Pipeline:
        tokenizer = default_tokenizer()
        runtime = runtime_dir()
        chain = AuditChain(config.audit_chain_file())
        return cls(
            engine=load_engine(),
            thresholds=load_thresholds(),
            tokenizer=tokenizer,
            history=build_history(tokenizer, runtime / "history.sqlite"),
            outbox=Outbox(runtime / "outbox.sqlite"),
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

    def start(self) -> None:
        if self.signer is not None:
            self.signer.start()

    def close(self) -> None:
        if self.signer is not None:
            self.signer.stop()

    def handle(self, request: PaymentRequest) -> Decision:
        """Entry point: the request is handed to `strip()` and never touched again (I1)."""
        started = time.perf_counter()
        return self.process(strip(request, self.tokenizer), started)

    def process(self, inp: FeatureInput, started: float | None = None) -> Decision:
        started = time.perf_counter() if started is None else started
        features = engineer(inp, self.history)

        kind, risk = decide(self.engine.score(features), self.thresholds)
        kind, risk, policy_reasons = apply_policy(kind, features, self.thresholds)
        reasons: list[Reason] = []
        if policy_reasons:  # the model saw nothing wrong, so its reasons would be empty or generic
            reasons = [Reason(code=c, level=lv) for c, lv in policy_reasons]
        elif kind != DecisionKind.ALLOW:
            pairs = self.engine.reasons(features)[:MAX_REASONS] or [
                (ReasonCode.OTHER_PATTERN, Level.LOW)
            ]
            reasons = [Reason(code=c, level=lv) for c, lv in pairs]
        self.history.record(inp.payee_token)

        decision_id = uuid.uuid4().hex
        decision = Decision(
            decision_id=decision_id,
            decision=kind,
            risk_level=risk,
            reason_codes=reasons,
            model_version=self.engine.version,
            server_ms=0.0,
        )
        if self.audit_append is not None:
            try:
                self.audit_append(decision)
            except OSError as exc:  # availability over audit: say so loudly instead of failing
                log_event("audit_error", decision_id=decision_id, error_type=type(exc).__name__)
        try:
            self.outbox.enqueue(
                ExplainJob(
                    decision_id=decision_id,
                    decision=kind,
                    risk_level=risk,
                    reasons=reasons,
                    language=inp.language,
                )
            )
        except sqlite3.Error as exc:  # the decision must not fail because the explainer path did
            log_event("outbox_error", decision_id=decision_id, error_type=type(exc).__name__)

        server_ms = round((time.perf_counter() - started) * 1000, 3)
        log_event(
            "decision",
            decision_id=decision_id,
            decision=kind.value,
            risk_level=risk.value,
            reason_codes=[r.code.value for r in reasons],
            model_version=self.engine.version,
            server_ms=server_ms,
        )
        return decision.model_copy(update={"server_ms": server_ms})

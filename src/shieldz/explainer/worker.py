"""Explainer worker: `python -m shieldz.explainer.worker` (the `explainer` container command).

Polls the outbox, never the decision path (I3). For each job it publishes the template text at
once, then tries the LLM and replaces the text if the output passes the guard. A slow or failing
LLM therefore costs nothing but the upgrade: the template explanation is already served.

The LLM sits behind `Generator`. `shieldz.explainer.granite.GraniteGenerator` (LinuxONE operator)
is the real one; without it (SHIELDZ_EXPLAINER=template) the worker is template-only.
"""

from __future__ import annotations

import os
import signal
import threading
import time
from typing import Protocol

from shieldz.clock import now_utc
from shieldz.config import runtime_dir
from shieldz.contracts import ExplainJob, Explanation, ExplanationSource
from shieldz.explainer.guard import validate_output, validate_prompt
from shieldz.explainer.journal import PromptJournal
from shieldz.explainer.prompt import build_prompt
from shieldz.explainer.template import TemplateExplainer
from shieldz.outbox.queue import FAILED, Outbox
from shieldz.privacy.redact_log import log_event, setup_logging

POLL_SECONDS = 0.2


class Generator(Protocol):
    name: str

    def generate(self, prompt: str) -> str:
        """Return the model's text for an already validated, digit-free prompt."""
        ...


class Worker:
    def __init__(
        self,
        outbox: Outbox,
        generator: Generator | None = None,
        journal: PromptJournal | None = None,
    ) -> None:
        self.outbox = outbox
        self.generator = generator
        self.journal = journal or PromptJournal()
        self.template = TemplateExplainer()

    def process(self, job: ExplainJob) -> Explanation:
        """Template first, LLM second. Returns what ended up stored."""
        final = self.template.explain(job)
        self.outbox.put_explanation(final, done=self.generator is None)
        if self.generator is None:
            self._journal(job, "", final, guard_passed=True)
            log_event("explained", decision_id=job.decision_id, source=final.source.value)
            return final

        prompt, text, ok = build_prompt(job), "", False
        try:
            ok, why = validate_prompt(prompt, job)
            if ok:
                text = self.generator.generate(prompt).strip()
                ok, why = validate_output(text)
        except Exception as exc:  # LLM trouble must never lose the job
            ok, why = False, type(exc).__name__
            log_event("generator_error", decision_id=job.decision_id, error_type=why)
        if ok:
            final = Explanation(
                decision_id=job.decision_id,
                text=text,
                source=ExplanationSource.GRANITE,
                language=job.language,
                ts=now_utc(),
            )
        self.outbox.put_explanation(final, done=True)  # marks done either way
        self._journal(job, prompt, final, guard_passed=ok)
        log_event(
            "explained",
            decision_id=job.decision_id,
            source=final.source.value,
            status="ok" if ok else "fallback",
        )
        return final

    def _journal(
        self, job: ExplainJob, prompt: str, final: Explanation, guard_passed: bool
    ) -> None:
        self.journal.record(
            job.decision_id, prompt, final.text, final.source.value, final.language.value,
            guard_passed,
        )  # fmt: skip

    def run_once(self) -> bool:
        job = self.outbox.claim_next()
        if job is None:
            return False
        try:
            self.process(job)
        except Exception as exc:
            self.outbox.mark(job.decision_id, FAILED)
            log_event("worker_error", decision_id=job.decision_id, error_type=type(exc).__name__)
        return True

    def run(self, stop: threading.Event) -> None:
        recovered = self.outbox.requeue_running()
        log_event("worker_start", count=recovered)
        while not stop.is_set():
            if not self.run_once():
                stop.wait(POLL_SECONDS)


def load_generator(name: str | None = None) -> Generator | None:
    name = name or os.environ.get("SHIELDZ_EXPLAINER", "template")
    if name == "template":
        return None
    if name == "granite":
        from shieldz.explainer.granite import GraniteGenerator

        return GraniteGenerator()
    raise ValueError(f"unknown explainer {name!r}")


def main() -> int:
    setup_logging()
    worker = Worker(Outbox(runtime_dir() / "outbox.sqlite"), load_generator())
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    started = time.monotonic()
    worker.run(stop)
    log_event("worker_stop", count=int(time.monotonic() - started))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

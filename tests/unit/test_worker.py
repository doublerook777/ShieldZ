"""Explainer worker: template first, LLM upgrade, guard fallback, crash recovery."""

from __future__ import annotations

import threading

import pytest

from shieldz.contracts import (
    DecisionKind,
    ExplainJob,
    ExplanationSource,
    Language,
    Level,
    Reason,
    ReasonCode,
)
from shieldz.explainer.journal import PromptJournal, load_journal
from shieldz.explainer.worker import Worker, load_generator
from shieldz.outbox.queue import DONE, FAILED, PENDING, RUNNING, Outbox

GOOD = "Please pause for a moment and call your bank on the number printed on your card."


class FakeLLM:
    name = "fake"

    def __init__(self, reply=GOOD, error=None):
        self.reply, self.error, self.prompts = reply, error, []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return self.reply


def job(i=0, decision=DecisionKind.BLOCK):
    return ExplainJob(
        decision_id=f"{i:032x}",
        decision=decision,
        risk_level=Level.HIGH,
        reasons=[Reason(code=ReasonCode.ACCOUNT_DRAIN, level=Level.HIGH)],
        language=Language.EN,
    )


@pytest.fixture
def box(tmp_path):
    return Outbox(tmp_path / "outbox.sqlite")


def worker(box, tmp_path, llm=None):
    return Worker(box, llm, PromptJournal(tmp_path / "prompts.jsonl"))


def test_template_only_mode_finishes_the_job(box, tmp_path):
    box.enqueue(job())
    assert worker(box, tmp_path).run_once() is True
    got = box.get_explanation(job().decision_id)
    assert got.source == ExplanationSource.TEMPLATE
    assert box.count(DONE) == 1 and worker(box, tmp_path).run_once() is False


def test_llm_text_replaces_template_when_guard_passes(box, tmp_path):
    llm = FakeLLM()
    box.enqueue(job())
    worker(box, tmp_path, llm).run_once()
    got = box.get_explanation(job().decision_id)
    assert got.source == ExplanationSource.GRANITE and got.text == GOOD
    assert len(llm.prompts) == 1 and not any(c.isdigit() for c in llm.prompts[0])
    [entry] = load_journal(tmp_path / "prompts.jsonl")
    assert entry["guard_passed"] is True and entry["source"] == "granite"


@pytest.mark.parametrize(
    "reply",
    ["Call 9876543210 now to be safe.", "Visit https://evil.example for help.", "short"],
)
def test_guard_rejection_keeps_the_template(box, tmp_path, reply):
    box.enqueue(job())
    worker(box, tmp_path, FakeLLM(reply)).run_once()
    got = box.get_explanation(job().decision_id)
    assert got.source == ExplanationSource.TEMPLATE
    assert load_journal(tmp_path / "prompts.jsonl")[0]["guard_passed"] is False
    assert box.count(DONE) == 1


def test_llm_exception_keeps_the_template_and_finishes(box, tmp_path):
    box.enqueue(job())
    worker(box, tmp_path, FakeLLM(error=RuntimeError("oom"))).run_once()
    assert box.get_explanation(job().decision_id).source == ExplanationSource.TEMPLATE
    assert box.count(DONE) == 1


def test_template_is_visible_while_the_llm_is_still_running(box, tmp_path):
    seen = {}

    class Slow(FakeLLM):
        def generate(self, prompt):
            seen["during"] = box.get_explanation(job().decision_id)
            return super().generate(prompt)

    box.enqueue(job())
    worker(box, tmp_path, Slow()).run_once()
    assert seen["during"].source == ExplanationSource.TEMPLATE
    assert box.count(RUNNING) == 0


def test_allow_jobs_are_never_picked_up(box, tmp_path):
    box.enqueue(job(decision=DecisionKind.ALLOW))
    assert worker(box, tmp_path).run_once() is False


def test_crashed_running_jobs_are_requeued_on_start(box, tmp_path):
    box.enqueue(job())
    box.claim_next()  # a worker took it, then died
    assert box.count(RUNNING) == 1
    stop = threading.Event()
    w = worker(box, tmp_path)
    threading.Timer(0.5, stop.set).start()
    w.run(stop)
    assert box.count(DONE) == 1 and box.count(PENDING) == 0


def test_processing_failure_marks_failed_not_lost(box, tmp_path):
    class Boom(Worker):
        def process(self, j):
            raise ValueError("bug")

    box.enqueue(job())
    Boom(box, None, PromptJournal(tmp_path / "p.jsonl")).run_once()
    assert box.count(FAILED) == 1


def test_load_generator():
    assert load_generator("template") is None
    with pytest.raises(ValueError):
        load_generator("nope")

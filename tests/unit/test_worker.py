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


def test_newest_job_is_explained_first_and_backlog_can_be_dropped(box):
    """After a burst the payment in front of the user must not wait behind hours of old jobs."""
    for i in range(5):
        box.enqueue(job(i))
    assert box.claim_next().decision_id == job(4).decision_id
    assert box.claim_next().decision_id == job(3).decision_id
    assert box.skip_pending() == 3  # jobs 0-2 are dropped, the two claimed ones stay `running`
    assert box.count(PENDING) == 0 and box.count(RUNNING) == 2 and box.count("skipped") == 3
    assert box.claim_next() is None


def test_same_prompt_is_generated_once_then_served_from_the_cache(box, tmp_path):
    llm = FakeLLM()
    w = worker(box, tmp_path, llm)
    box.enqueue(job(1))
    box.enqueue(job(2))  # a different decision with the same reasons/language: the same prompt
    w.run_once()
    w.run_once()
    assert len(llm.prompts) == 1
    texts = {box.get_explanation(job(i).decision_id).text for i in (1, 2)}
    assert texts == {GOOD}
    assert box.get_explanation(job(2).decision_id).source == ExplanationSource.GRANITE


def test_cache_key_depends_on_prompt_and_model_settings(box, tmp_path):
    from shieldz.explainer.worker import cache_key

    class Tagged(FakeLLM):
        cache_tag = "fake|max48"

    assert cache_key(FakeLLM(), "a") != cache_key(FakeLLM(), "b")
    assert cache_key(FakeLLM(), "a") != cache_key(Tagged(), "a")
    assert cache_key(Tagged(), "a") == cache_key(Tagged(), "a")


def test_rejected_output_is_never_cached_and_cached_text_is_guarded_again(box, tmp_path):
    bad = FakeLLM(reply="Send it to account 123456789012 now")
    w = worker(box, tmp_path, bad)
    box.enqueue(job(1))
    w.run_once()
    assert box.get_explanation(job(1).decision_id).source == ExplanationSource.TEMPLATE
    assert box._conn().execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0] == 0

    from shieldz.explainer.prompt import build_prompt
    from shieldz.explainer.worker import cache_key

    llm = FakeLLM()
    box.put_cached(cache_key(llm, build_prompt(job(2))), "Call 9876543210123 now")  # poisoned
    box.enqueue(job(2))
    worker(box, tmp_path, llm).run_once()
    assert box.get_explanation(job(2).decision_id).source == ExplanationSource.TEMPLATE
    assert llm.prompts == []  # it did not regenerate; it fell back, and the guard caught it


def test_trim_to_sentence():
    from shieldz.explainer.granite import trim_to_sentence

    assert trim_to_sentence("Pause now. Call your bank. Do not hu") == "Pause now. Call your bank."
    assert trim_to_sentence("Pause now. Call your bank.") == "Pause now. Call your bank."
    assert trim_to_sentence("कृपया रुकें। अपने बैंक को कॉल") == "कृपया रुकें।"
    assert trim_to_sentence("no full sentence here") == "no full sentence here"

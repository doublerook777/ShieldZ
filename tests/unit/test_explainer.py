"""Unit tests for M5 Granite Explainer components:

- prompt.py: build_prompt adhering to Invariant I2 (no digits, fixed template)
- guard.py: input allowlist firewall (exact match, no digits) + output guard (PII rejection)
- template.py: TemplateExplainer (EN, HI, TA deterministic fallback)
- journal.py: PromptJournal append-only audit log
- 1,000 fuzzed prompt rejection test (Gate M5 requirement)
"""

from __future__ import annotations

import random
import string
from pathlib import Path

from shieldz.contracts import (
    DecisionKind,
    ExplainJob,
    ExplanationSource,
    Language,
    Level,
    Reason,
    ReasonCode,
)
from shieldz.explainer.guard import validate_output, validate_prompt
from shieldz.explainer.journal import PromptJournal, load_journal
from shieldz.explainer.prompt import build_prompt
from shieldz.explainer.template import TemplateExplainer


def make_job(
    decision: DecisionKind = DecisionKind.BLOCK,
    risk: Level = Level.HIGH,
    reasons: list[Reason] | None = None,
    language: Language = Language.EN,
) -> ExplainJob:
    if reasons is None:
        reasons = [
            Reason(code=ReasonCode.AMOUNT_HIGH_VS_BALANCE, level=Level.HIGH),
            Reason(code=ReasonCode.NEW_RECIPIENT, level=Level.HIGH),
        ]
    return ExplainJob(
        decision_id="test-dec-123",
        decision=decision,
        risk_level=risk,
        reasons=reasons,
        language=language,
    )


def test_build_prompt_has_no_digits() -> None:
    job = make_job()
    prompt = build_prompt(job)
    assert not any(c.isdigit() for c in prompt), "Invariant I2 violated: prompt contains digits!"
    assert prompt.endswith("\nSimple words:")
    assert "This payment uses most of the funds in your account." in prompt  # from the enum


def test_validate_prompt_valid() -> None:
    job = make_job()
    prompt = build_prompt(job)
    valid, reason = validate_prompt(prompt, job)
    assert valid is True
    assert reason == "OK"


def test_validate_prompt_rejects_injected_digits() -> None:
    job = make_job()
    prompt = build_prompt(job) + "\nNote: Amount was 50000"
    valid, reason = validate_prompt(prompt, job)
    assert valid is False
    assert "digits" in reason.lower() or "canonical" in reason.lower()


def test_validate_prompt_rejects_injected_name() -> None:
    job = make_job()
    prompt = build_prompt(job).replace("Simple words:", "Payer Name: Ramesh\nSimple words:")
    valid, reason = validate_prompt(prompt, job)
    assert valid is False
    assert "canonical" in reason.lower()


def test_validate_prompt_rejects_extra_text() -> None:
    job = make_job()
    prompt = build_prompt(job) + " extra instructions"
    valid, _ = validate_prompt(prompt, job)
    assert valid is False


def test_validate_prompt_rejects_overlong() -> None:
    job = make_job()
    prompt = build_prompt(job) + ("a" * 2100)
    valid, reason = validate_prompt(prompt, job)
    assert valid is False
    assert "length" in reason.lower()


def test_validate_prompt_fuzz_1000_prompts() -> None:
    """Gate M5 requirement: 1,000 fuzzed prompts -> 0 accepted that break rules."""
    job = make_job()
    canonical_prompt = build_prompt(job)

    rng = random.Random(42)

    for _ in range(1000):
        mutation_type = rng.choice(["insert_digit", "insert_word", "truncate", "replace", "noise"])

        if mutation_type == "insert_digit":
            idx = rng.randint(0, len(canonical_prompt))
            digit = rng.choice(string.digits)
            fuzzed = canonical_prompt[:idx] + digit + canonical_prompt[idx:]
        elif mutation_type == "insert_word":
            idx = rng.randint(0, len(canonical_prompt))
            word = " " + "".join(rng.choices(string.ascii_letters, k=8)) + " "
            fuzzed = canonical_prompt[:idx] + word + canonical_prompt[idx:]
        elif mutation_type == "truncate":
            cut = rng.randint(1, len(canonical_prompt) - 5)
            fuzzed = canonical_prompt[:cut]
        elif mutation_type == "replace":
            idx = rng.randint(0, len(canonical_prompt) - 2)
            fuzzed = canonical_prompt[:idx] + "ZZ" + canonical_prompt[idx + 2 :]
        else:  # noise
            noise = "".join(rng.choices(string.printable, k=15))
            fuzzed = canonical_prompt + noise

        # The fuzzed prompt must NEVER be accepted
        valid, _ = validate_prompt(fuzzed, job)
        assert valid is False, f"Fuzzed prompt was wrongly accepted! Mutation: {mutation_type}"


def test_output_guard_clean_text() -> None:
    valid_text = (
        "This payment uses most of the funds in your account and is going to a new recipient. "
        "Please pause and verify this transfer by calling your bank on the official "
        "number on your card. "
        "Take 2 minutes to follow the 3 steps."
    )
    valid, reason = validate_output(valid_text)
    assert valid is True
    assert reason == "OK"


def test_output_guard_rejects_pii_shapes() -> None:
    # 1. 4+ digits (e.g. account / card / OTP)
    valid, reason = validate_output("Send funds to account 9876543210 immediately.")
    assert valid is False
    assert "digits" in reason.lower()

    # 2. Currency amounts
    valid, reason = validate_output("You are sending ₹500 to a friend.")
    assert valid is False
    assert "currency" in reason.lower()

    valid, reason = validate_output("Payment of 500 Rs requested.")
    assert valid is False
    assert "currency" in reason.lower()

    valid, reason = validate_output("INR 250 has been debited.")
    assert valid is False
    assert "currency" in reason.lower()

    # 3. Phone patterns
    valid, reason = validate_output("Call the officer at +91 98765 43210.")
    assert valid is False

    # 4. URLs
    valid, reason = validate_output("Click https://secure-bank-login.com to confirm.")
    assert valid is False
    assert "url" in reason.lower()

    # 5. Email / @
    valid, reason = validate_output("Send your ID to support@frauddesk.org.")
    assert valid is False
    assert "@" in reason.lower()


def test_template_explainer_en() -> None:
    explainer = TemplateExplainer()
    job = make_job(language=Language.EN)
    exp = explainer.explain(job)

    assert exp.decision_id == job.decision_id
    assert exp.source == ExplanationSource.TEMPLATE
    assert exp.language == Language.EN
    assert "uses most of the funds" in exp.text
    assert "receiving account is new" in exp.text
    assert "pause and verify" in exp.text

    valid, _ = validate_output(exp.text)
    assert valid is True


def test_template_explainer_hi_and_ta() -> None:
    explainer = TemplateExplainer()

    # Hindi
    job_hi = make_job(language=Language.HI)
    exp_hi = explainer.explain(job_hi)
    assert exp_hi.language == Language.HI
    assert "खाते" in exp_hi.text
    assert "कृपया रुकें" in exp_hi.text
    valid, _ = validate_output(exp_hi.text)
    assert valid is True

    # Tamil
    job_ta = make_job(language=Language.TA)
    exp_ta = explainer.explain(job_ta)
    assert exp_ta.language == Language.TA
    assert "கணக்கில்" in exp_ta.text
    assert "தயவுசெய்து" in exp_ta.text
    valid, _ = validate_output(exp_ta.text)
    assert valid is True


def test_prompt_journal(tmp_path: Path) -> None:
    journal_path = tmp_path / "journal" / "prompts.jsonl"
    journal = PromptJournal(journal_path)

    entry = journal.record(
        decision_id="dec-1",
        prompt="Decision: BLOCK.\nReasons:\n- OTHER_PATTERN: test",
        text="Please pause.",
        source="template",
        language="EN",
        guard_passed=True,
    )
    assert entry["decision_id"] == "dec-1"
    journal.close()

    records = load_journal(journal_path)
    assert len(records) == 1
    assert records[0]["decision_id"] == "dec-1"
    assert records[0]["guard_passed"] is True

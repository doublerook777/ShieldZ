"""Test Granite 4.0 LLM generation on LinuxONE s390x."""

import time

from shieldz.contracts import DecisionKind, ExplainJob, Language, Level, Reason, ReasonCode
from shieldz.explainer.granite import GraniteGenerator
from shieldz.explainer.guard import validate_output, validate_prompt
from shieldz.explainer.prompt import build_prompt


def test():
    print("Initializing GraniteGenerator...")
    t0 = time.time()
    g = GraniteGenerator()
    load_time = time.time() - t0
    print(f"Loaded in {load_time:.2f} s.")

    job = ExplainJob(
        decision_id="test-job-001",
        decision=DecisionKind.BLOCK,
        risk_level=Level.HIGH,
        reasons=[
            Reason(code=ReasonCode.ACCOUNT_DRAIN, level=Level.HIGH),
            Reason(code=ReasonCode.NEW_RECIPIENT, level=Level.HIGH),
        ],
        language=Language.EN,
    )
    prompt = build_prompt(job)
    print("\nValidated Prompt:\n" + prompt)

    ok_prompt, why_prompt = validate_prompt(prompt, job)
    assert ok_prompt, f"Prompt validation failed: {why_prompt}"

    t1 = time.time()
    text = g.generate(prompt)
    gen_time = time.time() - t1
    print(f"\nGenerated in {gen_time:.2f} s:\n{text}")

    ok_output, why_output = validate_output(text)
    print(f"\nOutput Guard passed: {ok_output} (reason: {why_output})")


if __name__ == "__main__":
    test()

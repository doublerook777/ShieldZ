"""M5 evidence that cannot be faked by the cache: run Granite on N distinct prompts.

    docker run -i --rm --network host -v $PWD/results:/app/results shieldz:latest \
        python scripts/granite_quality.py --n 30

Builds jobs for different combinations of reason codes (English; the LLM only rewrites English),
generates with the real model, and checks each output with the same guards the worker uses:
`validate_output` (no PII shapes) and `validate_quality` (no loops, contradictions, or missing
advice). Reports the pass rate and the generation time per prompt, and writes every output to
results/granite_quality.md so a human can read them. Run it with the explainer idle (it shares the
cores).
"""

from __future__ import annotations

import argparse
import itertools
import random
import sys
import time
from pathlib import Path

import numpy as np

from shieldz.contracts import DecisionKind, ExplainJob, Language, Level, Reason, ReasonCode
from shieldz.explainer.granite import GraniteGenerator
from shieldz.explainer.guard import validate_output, validate_prompt, validate_quality
from shieldz.explainer.prompt import build_prompt
from shieldz.explainer.template import TemplateExplainer

GATE_RATE = 0.8


def combos(rng: random.Random, n: int) -> list[tuple[ReasonCode, ...]]:
    codes = list(ReasonCode)
    every = [c for k in (1, 2, 3) for c in itertools.combinations(codes, k)]
    rng.shuffle(every)
    return every[:n]


def main(args: argparse.Namespace) -> int:
    rng = random.Random(args.seed)
    llm = GraniteGenerator()
    rows = []
    for chosen in combos(rng, args.n):
        decision = DecisionKind.BLOCK if len(chosen) >= 2 else DecisionKind.REVIEW
        job = ExplainJob(
            decision_id="0" * 32,
            decision=decision,
            risk_level=Level.HIGH if decision == DecisionKind.BLOCK else Level.MEDIUM,
            reasons=[Reason(code=c, level=Level.HIGH) for c in chosen],
            language=Language.EN,
        )
        prompt = build_prompt(job)
        assert validate_prompt(prompt, job)[0]
        t0 = time.monotonic()
        text = llm.generate(prompt).strip()
        seconds = time.monotonic() - t0
        ok, why = validate_output(text)
        if ok:
            ok, why = validate_quality(text)
        rows.append((job, text, ok, why, seconds))
        print(
            f"{'PASS' if ok else 'FAIL'} {seconds:5.1f}s {[c.value for c in chosen]}: {text[:90]}"
        )

    passed = [r for r in rows if r[2]]
    rate = len(passed) / len(rows)
    secs = np.asarray([r[4] for r in rows])
    lines = [
        "# Granite quality check (M5 evidence)",
        "",
        f"- Distinct prompts: {len(rows)} (cache bypassed: each one is a fresh generation)",
        f"- Passed the output and quality guards: {len(passed)} ({rate:.0%}); the rest fall "
        f"back to the human-written template. Gate: ≥ {GATE_RATE:.0%}",
        f"- Generation time: p50 {np.percentile(secs, 50):.1f} s, "
        f"p95 {np.percentile(secs, 95):.1f} s, max {secs.max():.1f} s",
        "",
        "## Every output",
    ]
    template = TemplateExplainer()
    for job, text, ok, why, seconds in rows:
        lines += [
            "",
            f"### {', '.join(r.code.value for r in job.reasons)}  "
            f"({'PASS' if ok else 'FAIL: ' + why}, {seconds:.1f} s)",
            f"- Granite: {text}",
            f"- Template: {template.explain(job).text}",
        ]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:7]))
    return 0 if rate >= GATE_RATE else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="results/granite_quality.md")
    sys.exit(main(ap.parse_args()))

"""M5 evidence: how many BLOCK/REVIEW explanations does Granite really write, and how fast?

    docker run --rm --network host -v $PWD/results:/app/results shieldz:latest \
        python scripts/granite_sample.py --n 50

Posts the three demo scenarios, then N more scam-like payments, and polls each explanation. The
worker publishes the template text first and swaps in Granite's when the guard accepts it, so a
decision counts as Granite once `source` becomes "granite". Writes results/sample_explanations.md
(a sample per scenario, the Granite rate, and time-to-template / time-to-Granite) and exits
non-zero if the rate is below 80% (M5 gate).
"""

from __future__ import annotations

import argparse
import copy
import sys
import time
from pathlib import Path

import httpx
import numpy as np

import demo_scenarios  # same folder; scripts/ is on sys.path when run as a script

GATE_RATE = 0.8


def scam_payment(i: int) -> dict:
    """A digital-arrest variant: a new payee each time, the whole balance."""
    payment = copy.deepcopy(demo_scenarios.SCENARIOS["digital_arrest"].payment)
    payment["payee_account"] = f"UPI-sample-escrow-{i:04d}@okaxis"
    payment["amount"] = payment["payer_balance_before"] = 100_000.0 + 137.0 * i
    return payment


def pct(values: list[float]) -> str:
    if not values:
        return "n/a"
    a = np.asarray(values)
    return (
        f"p50 {np.percentile(a, 50):.1f} s, p95 {np.percentile(a, 95):.1f} s, max {a.max():.1f} s"
    )


def main(args: argparse.Namespace) -> int:
    client = httpx.Client(base_url=args.url, timeout=30.0)
    jobs: dict[str, dict] = {}  # decision_id -> bookkeeping

    def submit(label: str, payment: dict) -> None:
        t0 = time.monotonic()
        body = client.post("/v1/score", json=payment).json()
        jobs[body["decision_id"]] = {
            "label": label,
            "decision": body["decision"],
            "reasons": [r["code"] for r in body["reason_codes"]],
            "t0": t0,
            "template_s": None,
            "granite_s": None,
            "source": None,
            "text": None,
        }

    for sc in demo_scenarios.SCENARIOS.values():
        submit(sc.id, sc.payment)
    for i in range(args.n):
        submit(f"sample-{i}", scam_payment(i))

    waiting = {d for d, j in jobs.items() if j["decision"] != "ALLOW"}
    deadline = time.monotonic() + args.timeout
    while waiting and time.monotonic() < deadline:
        for decision_id in list(waiting):
            r = client.get(f"/v1/explanations/{decision_id}")
            if r.status_code != 200:
                continue
            job, now = jobs[decision_id], time.monotonic()
            body = r.json()
            job["source"], job["text"] = body["source"], body["text"]
            if job["template_s"] is None:
                job["template_s"] = now - job["t0"]
            if body["source"] == "granite":
                job["granite_s"] = now - job["t0"]
                waiting.discard(decision_id)
        time.sleep(2.0)

    scored = [j for j in jobs.values() if j["label"].startswith("sample-")]
    granite = [j for j in scored if j["source"] == "granite"]
    first = pct([j["template_s"] for j in scored if j["template_s"] is not None])
    rate = len(granite) / len(scored) if scored else 0.0
    lines = [
        "# Sample explanations (M5 evidence)",
        "",
        f"- Sample jobs: {len(scored)}; written by Granite: {len(granite)} ({rate:.0%}); "
        f"gate: ≥ {GATE_RATE:.0%}",
        f"- Time to first (template) explanation: {first}",
        f"- Time to Granite explanation (queued behind earlier jobs): "
        f"{pct([j['granite_s'] for j in granite])}",
        "",
        "## One per scenario",
    ]
    for sc in demo_scenarios.SCENARIOS.values():
        job = next(j for j in jobs.values() if j["label"] == sc.id)
        lines += [
            "",
            f"### {sc.title}",
            f"- Decision: {job['decision']}; reasons: {', '.join(job['reasons']) or 'none'}",
            f"- Source: {job['source'] or 'n/a (ALLOW: no explanation needed)'}",
            f"> {job['text'] or '(none)'}",
        ]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:6]))
    print(f"wrote {args.out}")
    return 0 if rate >= GATE_RATE else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--timeout", type=float, default=1800.0, help="seconds to wait for Granite")
    ap.add_argument("--out", default="results/sample_explanations.md")
    sys.exit(main(ap.parse_args()))

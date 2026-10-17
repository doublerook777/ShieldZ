"""Fill the Granite prompt cache before a demo or a recording.

    docker run -i --rm --network host shieldz:latest python scripts/prewarm_explanations.py

Granite needs ~10-16 s per explanation, so the demo would show the template text first and wait.
The cache is keyed by the validated prompt (decision + reason codes + language, no personal data),
so each combination has to be generated only once. This posts every demo scenario in every
language, both as `scripts/demo_scenarios.py` sends it and as the demo UI form sends it (the UI
fixes `payee_balance_before` to 0 and sets `payee_is_merchant` from the type, which can change the
reason codes and therefore the prompt), and waits until Granite's text is in place.

Say so in the video: these are Granite outputs generated beforehand and cached, not generated live
for each click.
"""

from __future__ import annotations

import argparse
import copy
import sys
import time

import httpx

import demo_scenarios  # same folder; scripts/ is on sys.path when run as a script

LANGUAGES = ("EN", "HI", "TA")


def ui_shape(payment: dict) -> dict:
    """What index.html sends for the same form values."""
    shaped = copy.deepcopy(payment)
    shaped["payee_balance_before"] = 0.0
    shaped["payee_is_merchant"] = shaped["tx_type"] == "PAYMENT"
    return shaped


def main(args: argparse.Namespace) -> int:
    client = httpx.Client(base_url=args.url, timeout=30.0)
    pending: dict[str, str] = {}  # decision_id -> label
    seen_prompts: set[tuple] = set()
    for sc in demo_scenarios.SCENARIOS.values():
        for lang in LANGUAGES:
            for shape, payment in (("cli", sc.payment), ("ui", ui_shape(sc.payment))):
                body = client.post("/v1/score", json=payment | {"language": lang}).json()
                label = f"{sc.id}/{lang}/{shape}: {body['decision']}"
                if body["decision"] == "ALLOW":
                    print(f"  {label} (no explanation needed)")
                    continue
                combo = (body["decision"], tuple(r["code"] for r in body["reason_codes"]), lang)
                if combo in seen_prompts:
                    print(f"  {label} (same prompt as an earlier one: cached after it)")
                    continue
                seen_prompts.add(combo)
                pending[body["decision_id"]] = label
                print(f"  {label}: queued")

    started, deadline = time.monotonic(), time.monotonic() + args.timeout
    while pending and time.monotonic() < deadline:
        for decision_id, label in list(pending.items()):
            r = client.get(f"/v1/explanations/{decision_id}")
            if r.status_code == 200 and r.json()["source"] == "granite":
                print(f"  {label}: Granite ready after {time.monotonic() - started:.0f} s")
                del pending[decision_id]
        time.sleep(2.0)
    for label in pending.values():
        print(f"  NOT READY: {label}")
    print(f"{len(seen_prompts) - len(pending)} of {len(seen_prompts)} distinct prompts cached")
    return 0 if not pending else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--timeout", type=float, default=900.0)
    sys.exit(main(ap.parse_args()))

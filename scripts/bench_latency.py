"""Latency benchmark for POST /v1/score. Run on the VM itself, so network latency isn't measured.

    docker exec shieldz-api python scripts/bench_latency.py --n 5000 --warmup 500 \
        --concurrency 1 8 --out results/latency_<tag>.json

Reports client-side and server-side (`server_ms`) p50/p95/p99 per concurrency level, and checks
that the outbox gained exactly one row per request when it can read the outbox file.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import multiprocessing as mp
import platform
import random
import sqlite3
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import numpy as np

GATE_P99_MS = 50.0
JSON = {"content-type": "application/json"}


def make_payment(rng: random.Random, i: int) -> dict:
    """Synthetic traffic: about one in five looks like a drain to a new payee."""
    risky = rng.random() < 0.2
    balance = round(rng.uniform(2_000, 900_000), 2)
    return {
        "payer_name": f"Bench Payer {i}",
        "payer_phone": f"+9190{rng.randrange(10**8):08d}",
        "payer_account": f"BENCH-{rng.randrange(10**6):06d}",
        "payee_name": f"Bench Payee {i}",
        "payee_account": f"BENCH-PAYEE-{rng.randrange(10**5):05d}",
        "memo": "bench",
        "tx_type": rng.choice(
            ["TRANSFER", "CASH_OUT"] if risky else ["PAYMENT", "CASH_IN", "DEBIT"]
        ),
        "amount": balance if risky else round(balance * rng.uniform(0.001, 0.2), 2),
        "payer_balance_before": balance,
        "payee_balance_before": 0 if risky else None,
        "payee_is_merchant": not risky,
        "timestamp": f"2026-10-17T{rng.randrange(24):02d}:00:00+05:30",
        "language": rng.choice(["EN", "HI", "TA"]),
    }


def pct(values: list[float]) -> dict:
    a = np.asarray(values)
    return {f"p{q}": round(float(np.percentile(a, q)), 3) for q in (50, 95, 99)} | {
        "max": round(float(a.max()), 3)
    }


def _level_sync(args: tuple):
    return asyncio.run(_level(*args))


async def _level(url: str, n: int, concurrency: int, seed: int):
    rng = random.Random(seed)
    # serialise before the clock starts, so the client's own JSON work isn't measured
    payloads = [json.dumps(make_payment(rng, i)).encode() for i in range(n)]
    queue: asyncio.Queue = asyncio.Queue()
    for p in payloads:
        queue.put_nowait(p)
    client_ms: list[float] = []
    server_ms: list[float] = []
    decisions: dict[str, int] = {}
    errors = 0

    async def worker() -> None:
        nonlocal errors
        while True:
            try:
                payload = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            t0 = time.perf_counter()
            r = await client.post(url + "/v1/score", content=payload, headers=JSON)
            elapsed = (time.perf_counter() - t0) * 1000
            if r.status_code != 200:
                errors += 1
                continue
            body = r.json()
            client_ms.append(elapsed)
            server_ms.append(body["server_ms"])
            decisions[body["decision"]] = decisions.get(body["decision"], 0) + 1

    limits = httpx.Limits(max_connections=concurrency)
    async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
        await asyncio.gather(*(worker() for _ in range(concurrency)))
    return client_ms, server_ms, decisions, errors


def outbox_count(path: Path) -> int | None:
    if not path.exists():
        return None
    with sqlite3.connect(path) as db:
        return db.execute("SELECT COUNT(*) FROM explain_jobs").fetchone()[0]


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def run_level(url: str, n: int, concurrency: int, procs: int, seed: int):
    """`concurrency` connections spread over client processes, so one busy Python client doesn't
    become the bottleneck and inflate the tail (the load generator shares the VM with the api)."""
    procs = max(1, min(procs, concurrency))
    per_proc, extra = divmod(concurrency, procs)
    jobs = [
        (url, n // procs + (i < n % procs), per_proc + (i < extra), seed + i) for i in range(procs)
    ]
    with mp.get_context("spawn").Pool(procs) as pool:
        parts = pool.map(_level_sync, jobs)
    decisions: dict[str, int] = {}
    for _, _, d, _ in parts:
        for k, v in d.items():
            decisions[k] = decisions.get(k, 0) + v
    return (
        [x for p in parts for x in p[0]],
        [x for p in parts for x in p[1]],
        decisions,
        sum(p[3] for p in parts),
    )


def main(args: argparse.Namespace) -> int:
    outbox_path = Path(args.outbox)
    health = httpx.get(args.url + "/healthz", timeout=10.0).json()
    run_level(args.url, args.warmup, 8, args.procs, seed=1)
    before = outbox_count(outbox_path)
    levels = {}
    sent = 0
    for c in args.concurrency:
        cm, sm, decisions, errors = run_level(args.url, args.n, c, args.procs, seed=100 * c)
        sent += len(cm)
        levels[str(c)] = {
            "requests": len(cm),
            "errors": errors,
            "client_ms": pct(cm),
            "server_ms": pct(sm),
            "decisions": decisions,
            "pass": errors == 0 and pct(cm)["p99"] < GATE_P99_MS,
        }
    after = outbox_count(outbox_path)

    outbox_ok = None if before is None or after is None else (after - before) == sent
    result = {
        "ts": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "platform": health.get("platform", platform.machine()),
        "engine": health.get("engine"),
        "model_version": health.get("model_version"),
        "n_per_level": args.n,
        "client_procs": args.procs,
        "warmup": args.warmup,
        "gate_p99_ms": GATE_P99_MS,
        "levels": levels,
        "outbox_rows_added": None if before is None or after is None else after - before,
        "outbox_one_row_per_request": outbox_ok,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
    for c, lv in levels.items():
        print(
            f"concurrency {c}: client p50/p95/p99 = {lv['client_ms']['p50']}/"
            f"{lv['client_ms']['p95']}/{lv['client_ms']['p99']} ms, "
            f"server p99 = {lv['server_ms']['p99']} ms, errors = {lv['errors']}"
        )
    print(f"outbox one row per request: {outbox_ok}  (wrote {args.out})")
    return 0 if all(lv["pass"] for lv in levels.values()) and outbox_ok is not False else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--warmup", type=int, default=500)
    ap.add_argument("--concurrency", type=int, nargs="+", default=[1, 8])
    ap.add_argument("--procs", type=int, default=4, help="client processes (default 4)")
    ap.add_argument("--outbox", default="artifacts/runtime/outbox.sqlite")
    ap.add_argument("--out", required=True)
    raise SystemExit(main(ap.parse_args()))

"""Several api workers share one runtime dir: history, outbox and pepper must stay consistent."""

from __future__ import annotations

import multiprocessing as mp
from pathlib import Path

from shieldz.contracts import DecisionKind, ExplainJob, Language, Level
from shieldz.features.history import SqliteHistoryStore
from shieldz.outbox.queue import Outbox
from shieldz.privacy.tokenize import Tokenizer, load_pepper

WORKERS, PER_WORKER = 4, 150
CTX = mp.get_context("spawn")


def _history_worker(path: str, pepper_file: str) -> None:
    tk = Tokenizer(load_pepper(Path(pepper_file)))
    store = SqliteHistoryStore(path)
    store.seed_from_csv(tk)  # every worker seeds on start; only one may win
    for _ in range(PER_WORKER):
        store.record("shared-token")


def _outbox_worker(path: str, tag: str) -> None:
    box = Outbox(path)
    for i in range(PER_WORKER):
        box.enqueue(
            ExplainJob(
                decision_id=f"{tag}{i:04d}",
                decision=DecisionKind.BLOCK,
                risk_level=Level.HIGH,
                reasons=[],
                language=Language.EN,
            )
        )


def _run(target, argsets) -> None:
    procs = [CTX.Process(target=target, args=a) for a in argsets]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=60)
    assert all(p.exitcode == 0 for p in procs)


def test_concurrent_history_counts_and_single_seed(tmp_path):
    db, pepper = str(tmp_path / "h.sqlite"), str(tmp_path / "keys" / "pepper")
    _run(_history_worker, [(db, pepper)] * WORKERS)
    store = SqliteHistoryStore(db)
    tk = Tokenizer(load_pepper(Path(pepper)))
    assert store.count("shared-token") == WORKERS * PER_WORKER
    assert store.count(tk.token("DEMO-ELECTRICITY-BOARD")) == 5200  # seeded exactly once


def test_concurrent_outbox_inserts(tmp_path):
    db = str(tmp_path / "outbox.sqlite")
    _run(_outbox_worker, [(db, f"w{n}") for n in range(WORKERS)])
    assert Outbox(db).count() == WORKERS * PER_WORKER


def _pepper_worker(path: str, out: str) -> None:
    Path(out).write_text(load_pepper(Path(path)).hex())


def test_pepper_race_gives_everyone_the_same_key(tmp_path):
    pepper = str(tmp_path / "keys" / "pepper")
    outs = [str(tmp_path / f"o{n}") for n in range(8)]
    _run(_pepper_worker, [(pepper, o) for o in outs])
    values = {open(o).read() for o in outs}
    assert len(values) == 1 and len(next(iter(values))) == 64
    assert load_pepper(Path(pepper)).hex() in values
    assert not [p for p in (tmp_path / "keys").iterdir() if p.name != "pepper"]

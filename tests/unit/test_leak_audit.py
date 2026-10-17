import sqlite3

from shieldz.leak_audit.canaries import generate_canaries
from shieldz.leak_audit.replay import run_leak_audit
from shieldz.leak_audit.scanner import LeakScanner
from shieldz.leak_audit.scorecard import LeakScorecard
from shieldz.leak_audit.sinks import SinkRegistry


def test_sink_registry_sqlite_extraction(tmp_path):
    db_file = tmp_path / "test.sqlite"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE users (id INT, name TEXT, account TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice Tester', 'ACC123456789')")
    conn.commit()
    conn.close()

    canaries = generate_canaries(n=10, seed=42)
    scanner = LeakScanner(canaries)

    registry = SinkRegistry(runtime_dir=tmp_path)
    registry.register_file("test_db", db_file)

    findings, bytes_per_sink = registry.scan_all(scanner)
    assert "test_db" in bytes_per_sink
    assert bytes_per_sink["test_db"] > 0
    assert len(findings) == 0  # No canary data was inserted


def test_scorecard_pass_criteria():
    scorecard = LeakScorecard.create(
        environment="test",
        records_replayed=100,
        bytes_per_sink={"sink1": 500, "sink2": 1200},
        findings=[],
        positive_control_planted=10,
        positive_control_found=10,
        negative_control_decoys=100,
        negative_control_hits=0,
    )
    assert scorecard.status == "PASS"
    assert scorecard.positive_control_passed is True
    assert scorecard.negative_control_passed is True
    assert "✅ PASS (0 Leaks)" in scorecard.to_markdown()


def test_scorecard_fail_on_positive_control():
    scorecard = LeakScorecard.create(
        environment="test",
        records_replayed=100,
        bytes_per_sink={"sink1": 500},
        findings=[],
        positive_control_planted=10,
        positive_control_found=8,  # Missing 2 planted leaks!
        negative_control_decoys=100,
        negative_control_hits=0,
    )
    assert scorecard.status == "FAIL"
    assert scorecard.positive_control_passed is False


def test_run_leak_audit_end_to_end(tmp_path):
    runtime_dir = tmp_path / "runtime"
    results_dir = tmp_path / "results"

    scorecard = run_leak_audit(
        runtime_dir=runtime_dir,
        n_canaries=50,
        n_decoys=50,
        environment="local_test",
        results_dir=results_dir,
    )

    assert scorecard.status == "PASS"
    assert scorecard.records_replayed == 50
    assert scorecard.leaks_exact == 0
    assert scorecard.leaks_variant == 0
    assert scorecard.leaks_partial == 0
    assert scorecard.positive_control_passed is True
    assert scorecard.negative_control_passed is True

    # Check scorecard files were written
    json_path = results_dir / "leak_scorecard_local_test.json"
    md_path = results_dir / "leak_scorecard_local_test.md"
    assert json_path.exists()
    assert md_path.exists()

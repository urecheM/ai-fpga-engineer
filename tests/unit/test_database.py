from __future__ import annotations

import json
import sqlite3

from hdleval.registry.database import ExperimentDB
from hdleval.registry.experiment import ExperimentRecord, environment_fingerprint

_LEGACY_SCHEMA = """
CREATE TABLE runs (
    run_id TEXT,
    experiment TEXT,
    benchmark TEXT,
    benchmark_version TEXT,
    model TEXT,
    prompt TEXT,
    seed INTEGER,
    trial INTEGER,
    passed INTEGER,
    failure_class TEXT,
    duration_s REAL,
    git_commit TEXT,
    started_at REAL,
    record_json TEXT,
    PRIMARY KEY (run_id, benchmark, trial)
);
"""


def test_db_roundtrip(tmp_path):
    db = ExperimentDB(tmp_path / "db.sqlite")
    rec = ExperimentRecord(
        experiment="e",
        run_id="r1",
        benchmark="b",
        benchmark_version="1.0.0",
        model="m",
        model_id="mid",
        prompt="p",
        seed=1,
        trial=0,
        passed=True,
    )
    db.insert(rec)
    recs = db.all_records("e")
    assert len(recs) == 1 and recs[0]["benchmark"] == "b"
    assert "e" in db.experiments()
    db.close()


def test_environment_fingerprint_has_keys():
    fp = environment_fingerprint()
    assert {"os", "python", "machine", "git_commit"} <= set(fp)


def test_db_roundtrip_persists_cost_fields(tmp_path):
    db = ExperimentDB(tmp_path / "db.sqlite")
    rec = ExperimentRecord(
        experiment="e",
        run_id="r2",
        benchmark="b",
        benchmark_version="1.0.0",
        model="m",
        model_id="claude-sonnet-5",
        prompt="p",
        seed=1,
        trial=0,
        passed=True,
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.00105,
    )
    db.insert(rec)
    recs = db.all_records("e")
    assert recs[0]["input_tokens"] == 100
    assert recs[0]["output_tokens"] == 50
    assert recs[0]["cost_usd"] == 0.00105
    db.close()


def test_opens_and_migrates_legacy_db_without_cost_columns(tmp_path):
    legacy_path = tmp_path / "legacy.sqlite"
    conn = sqlite3.connect(legacy_path)
    conn.executescript(_LEGACY_SCHEMA)
    conn.execute(
        "INSERT INTO runs (run_id, experiment, benchmark, benchmark_version, model, "
        "prompt, seed, trial, passed, failure_class, duration_s, git_commit, "
        "started_at, record_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "legacy-run",
            "baseline-v1",
            "arith_adder8",
            "1.0.0",
            "reference-golden",
            "direct",
            1,
            0,
            1,
            "none",
            0.1,
            "abc123",
            0.0,
            json.dumps({"benchmark": "arith_adder8", "passed": True}),
        ),
    )
    conn.commit()
    conn.close()

    db = ExperimentDB(legacy_path)
    recs = db.all_records("baseline-v1")
    assert len(recs) == 1 and recs[0]["benchmark"] == "arith_adder8"

    rec = ExperimentRecord(
        experiment="baseline-v1",
        run_id="new-run",
        benchmark="arith_alu8",
        benchmark_version="1.0.0",
        model="m",
        model_id="claude-sonnet-5",
        prompt="p",
        seed=1,
        trial=0,
        passed=True,
        input_tokens=10,
        output_tokens=5,
        cost_usd=0.0001,
    )
    db.insert(rec)
    recs = db.all_records("baseline-v1")
    assert len(recs) == 2
    db.close()

from __future__ import annotations

from hdleval.registry.database import ExperimentDB
from hdleval.registry.experiment import ExperimentRecord, environment_fingerprint


def test_db_roundtrip(tmp_path):
    db = ExperimentDB(tmp_path / "db.sqlite")
    rec = ExperimentRecord(experiment="e", run_id="r1", benchmark="b", benchmark_version="1.0.0",
                           model="m", model_id="mid", prompt="p", seed=1, trial=0, passed=True)
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
    rec = ExperimentRecord(experiment="e", run_id="r2", benchmark="b", benchmark_version="1.0.0",
                           model="m", model_id="claude-sonnet-5", prompt="p", seed=1, trial=0,
                           passed=True, input_tokens=100, output_tokens=50, cost_usd=0.00105)
    db.insert(rec)
    recs = db.all_records("e")
    assert recs[0]["input_tokens"] == 100
    assert recs[0]["output_tokens"] == 50
    assert recs[0]["cost_usd"] == 0.00105
    db.close()

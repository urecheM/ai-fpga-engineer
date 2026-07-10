from __future__ import annotations

from hdleval.config.schema import (
    BenchmarkSelector, ExperimentConfig, ModelConfig, PromptConfig,
)
from hdleval.evaluation.runner import run_experiment


def test_run_small_experiment(tmp_path):
    exp = ExperimentConfig(
        name="small",
        models=[ModelConfig(name="reference-golden", provider="reference")],
        prompts=[PromptConfig(name="direct", template="{specification}")],
        benchmarks=BenchmarkSelector(categories=["arithmetic"]),
        trials=1,
    )
    results, records = run_experiment(
        exp, out_dir=tmp_path / "results", db_path=tmp_path / "db.sqlite")
    assert results and len(results) == len(records)
    assert all(r.passed for r in results)  # reference provider is the upper bound
    assert (tmp_path / "results" / "small.jsonl").exists()

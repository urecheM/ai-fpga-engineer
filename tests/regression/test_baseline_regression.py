"""Golden regression: the deterministic providers must not silently drift."""

from __future__ import annotations

from hdleval.config.schema import (
    BenchmarkSelector,
    ExperimentConfig,
    ModelConfig,
    PromptConfig,
)
from hdleval.evaluation.runner import run_experiment


def _run(model_name, provider, extra, tmp_path):
    exp = ExperimentConfig(
        name="reg",
        models=[ModelConfig(name=model_name, provider=provider, seed=7, extra=extra)],
        prompts=[PromptConfig(name="direct", template="{specification}")],
        benchmarks=BenchmarkSelector(suite_version="v1"),
        trials=1,
        seed=20260707,
    )
    results, _ = run_experiment(exp, out_dir=tmp_path / "r", db_path=tmp_path / "d.sqlite")
    return results


def test_reference_full_pass(tmp_path):
    results = _run("reference-golden", "reference", {}, tmp_path)
    # reference provider is the upper bound: all benchmarks pass
    assert all(r.passed for r in results)
    assert len(results) >= 15


def test_synthetic_is_deterministic(tmp_path):
    r1 = _run("synthetic-mid", "synthetic", {"fidelity": 0.75}, tmp_path / "a")
    r2 = _run("synthetic-mid", "synthetic", {"fidelity": 0.75}, tmp_path / "b")
    p1 = sorted((r.benchmark, r.passed) for r in r1)
    p2 = sorted((r.benchmark, r.passed) for r in r2)
    assert p1 == p2, "synthetic provider must be deterministic across runs"

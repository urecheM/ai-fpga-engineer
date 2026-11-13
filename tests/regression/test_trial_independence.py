from __future__ import annotations

from collections import defaultdict

from hdleval.config.schema import (
    BenchmarkSelector,
    ExperimentConfig,
    ModelConfig,
    PromptConfig,
)
from hdleval.evaluation.runner import run_experiment
from hdleval.models.anthropic_provider import _cache_key
from hdleval.models.base import ModelRequest, derive_run_seed


def _exp(trials: int) -> ExperimentConfig:
    return ExperimentConfig(
        name="trial-independence",
        models=[
            ModelConfig(
                name="synthetic-mid", provider="synthetic", seed=7, extra={"fidelity": 0.75}
            )
        ],
        prompts=[PromptConfig(name="direct", template="{specification}")],
        benchmarks=BenchmarkSelector(suite_version="v1"),
        trials=trials,
        seed=20260707,
    )


def test_run_seed_depends_on_trial():
    seeds = {derive_run_seed(1, "m", "b", t) for t in range(10)}
    assert len(seeds) == 10
    assert derive_run_seed(1, "m", "b", 0) == derive_run_seed(1, "m", "b", 0)


def test_trials_are_not_all_identical(tmp_path):
    results, _ = run_experiment(
        _exp(trials=3), out_dir=tmp_path / "r", db_path=tmp_path / "d.sqlite"
    )
    outcomes: dict[str, set[str]] = defaultdict(set)
    for r in results:
        outcomes[r.benchmark].add(f"{r.passed}:{r.failure_class}")
    varying = [b for b, o in outcomes.items() if len(o) > 1]
    assert varying, "all trials identical for every benchmark: trials are not independent"


def test_api_cache_key_differs_per_trial():
    cfg = ModelConfig(name="m", provider="anthropic", model_id="x")
    keys = {
        _cache_key(
            ModelRequest(
                system="s",
                prompt="p",
                config=cfg,
                trial=t,
                run_seed=derive_run_seed(1, "m", "b", t),
            )
        )
        for t in range(3)
    }
    assert len(keys) == 3

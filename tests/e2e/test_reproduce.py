"""End-to-end: benchmark build + experiment + report generation."""
from __future__ import annotations

import json

from hdleval.benchmarks.loader import load_suite
from hdleval.config.schema import (
    BenchmarkSelector, ExperimentConfig, ModelConfig, PromptConfig,
)
from hdleval.evaluation.runner import run_experiment
from hdleval.leaderboard.aggregate import build_leaderboard
from hdleval.reporting import write_all_figures, write_all_reports


def test_end_to_end(tmp_path):
    exp = ExperimentConfig(
        name="e2e",
        models=[ModelConfig(name="reference-golden", provider="reference"),
                ModelConfig(name="synthetic-low", provider="synthetic", seed=7,
                            extra={"fidelity": 0.6})],
        prompts=[PromptConfig(name="direct", template="{specification}")],
        benchmarks=BenchmarkSelector(suite_version="v1"),
        trials=2, seed=1,
    )
    results, records = run_experiment(
        exp, out_dir=tmp_path / "res", db_path=tmp_path / "db.sqlite")
    suite = {b.id: b.to_dict() for b in load_suite("v1")}
    lb = build_leaderboard([r.to_dict() for r in records], suite)
    written = write_all_reports([r.to_dict() for r in records], lb, tmp_path / "res", "e2e")
    figs = write_all_figures(lb.to_dict(), [r.to_dict() for r in records], tmp_path / "res" / "figures")

    assert lb.overall
    # reference should outrank the low-fidelity synthetic model
    ranks = {r["model"]: r["pass_rate"] for r in lb.overall}
    assert ranks["reference-golden"] >= ranks["synthetic-low"]
    for path in {**written, **figs}.values():
        assert json.dumps(path)  # all paths recorded

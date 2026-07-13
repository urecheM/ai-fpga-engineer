"""Drive a full experiment: models x prompts x benchmarks x trials."""

from __future__ import annotations

from pathlib import Path

from ..benchmarks.loader import load_suite, select
from ..config.schema import ExperimentConfig
from ..logging.structured import StructuredLogger
from ..models.registry import build_provider
from ..registry.database import ExperimentDB
from ..registry.experiment import ExperimentRecord
from .harness import EvaluationHarness
from .result import BenchmarkResult


def run_experiment(
    exp: ExperimentConfig,
    *,
    out_dir: str | Path = "results/raw",
    db_path: str | Path = "experiments/registry.sqlite",
    benchmarks_root: str | Path | None = None,
) -> tuple[list[BenchmarkResult], list[ExperimentRecord]]:
    exp.validate()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    logger = StructuredLogger(out / f"{exp.name}.jsonl")
    harness = EvaluationHarness(exp, logger=logger, benchmarks_root=benchmarks_root)
    db = ExperimentDB(db_path)

    suite = load_suite(exp.benchmarks.suite_version, benchmarks_root)
    chosen = select(suite, exp.benchmarks)

    results: list[BenchmarkResult] = []
    records: list[ExperimentRecord] = []
    for model_cfg in exp.models:
        provider = build_provider(model_cfg)
        for prompt_cfg in exp.prompts:
            for bench in chosen:
                for trial in range(exp.trials):
                    res, rec = harness.evaluate(bench, provider, model_cfg, prompt_cfg, trial)
                    results.append(res)
                    records.append(rec)
                    db.insert(rec)
    logger.close()
    db.close()
    return results, records

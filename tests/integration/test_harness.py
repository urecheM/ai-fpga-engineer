from __future__ import annotations

from hdleval.benchmarks.loader import load_suite
from hdleval.config.schema import ExperimentConfig, ModelConfig, PromptConfig
from hdleval.evaluation.harness import EvaluationHarness
from hdleval.models.reference import ReferenceProvider


def _exp():
    return ExperimentConfig(
        name="itest",
        models=[ModelConfig(name="reference-golden", provider="reference")],
        prompts=[PromptConfig(name="direct", template="{specification}")],
    )


def test_reference_provider_passes_adder():
    suite = load_suite("v1")
    bench = next(b for b in suite if b.id == "arith_adder8")
    harness = EvaluationHarness(_exp())
    result, rec = harness.evaluate(
        bench, ReferenceProvider(), _exp().models[0], _exp().prompts[0], trial=0
    )
    assert result.hdl and "adder8" in result.hdl
    assert result.passed
    assert rec.passed and rec.duration_s >= 0
    assert result.stage("parse").status == "ok"


def test_no_reference_is_no_code():
    from hdleval.benchmarks.schema import Benchmark

    empty = Benchmark(
        id="empty",
        version="1.0.0",
        category="arithmetic",
        title="x",
        specification="do nothing",
        entity="empty",
    )
    harness = EvaluationHarness(_exp())
    result, _ = harness.evaluate(
        empty, ReferenceProvider(), _exp().models[0], _exp().prompts[0], trial=0
    )
    assert not result.passed
    assert result.failure_class == "no_code_generated"

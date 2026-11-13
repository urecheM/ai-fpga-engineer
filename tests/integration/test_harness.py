from __future__ import annotations

import pytest

from conftest import reference_verdict_ok
from hdleval.benchmarks.loader import load_suite
from hdleval.config.schema import ExperimentConfig, ModelConfig, PromptConfig
from hdleval.evaluation.harness import EvaluationHarness
from hdleval.models.reference import ReferenceProvider
from hdleval.models.synthetic import SyntheticProvider
from hdleval.toolchain.detect import detect


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
    assert reference_verdict_ok(result)
    assert rec.passed == result.passed and rec.duration_s >= 0
    assert result.stage("parse").status == "ok"


def test_synthetic_run_records_tokens_and_zero_cost():
    suite = load_suite("v1")
    bench = next(b for b in suite if b.id == "arith_adder8")
    harness = EvaluationHarness(_exp())
    _, rec = harness.evaluate(
        bench, SyntheticProvider(), _exp().models[0], _exp().prompts[0], trial=0
    )
    assert rec.input_tokens > 0
    assert rec.output_tokens > 0
    assert rec.cost_usd == 0.0


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


@pytest.mark.skipif(
    not (detect().has("yosys") and detect().ghdl_plugin),
    reason="yosys/ghdl-yosys-plugin not available",
)
def test_resource_counts_nonzero_for_ctrl_debounce():
    suite = load_suite("v1")
    bench = next(b for b in suite if b.id == "ctrl_debounce")
    harness = EvaluationHarness(_exp())
    result, _ = harness.evaluate(
        bench, ReferenceProvider(), _exp().models[0], _exp().prompts[0], trial=0
    )
    resources = result.metrics["resources"]
    assert resources["available"] is True
    assert resources["luts"] > 0
    assert resources["ffs"] > 0


class _WrongInterfaceProvider:
    """Returns the adder reference with the carry-out port renamed."""

    name = "wrong-iface"
    available = True

    def generate(self, request):
        from hdleval.models.base import ModelResponse

        ref = request.context["reference_hdl"].replace("cout", "carry_out")
        return ModelResponse(text=f"```vhdl\n{ref}\n```", provider=self.name, model_id="x")


def test_interface_mismatch_is_classified():
    bench = next(b for b in load_suite("v1") if b.id == "arith_adder8")
    harness = EvaluationHarness(_exp())
    result, _ = harness.evaluate(
        bench, _WrongInterfaceProvider(), _exp().models[0], _exp().prompts[0], trial=0
    )
    if detect().has("ghdl"):
        assert result.failure_class == "interface_mismatch"
    assert result.stage("interface").status == "fail"
    assert "missing port cout" in result.stage("interface").detail["problems"]


def test_prompt_contains_entity_declaration():
    from hdleval.evaluation.harness import with_interface

    bench = next(b for b in load_suite("v1") if b.id == "arith_adder8")
    from hdleval.benchmarks.loader import reference_hdl

    spec = with_interface(bench.specification, reference_hdl(bench), bench.entity)
    assert "entity adder8 is" in spec and "cout" in spec

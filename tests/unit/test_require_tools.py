from __future__ import annotations

import sys

import pytest

from hdleval.config.schema import ExperimentConfig, ModelConfig, PromptConfig, SynthesisConfig
from hdleval.evaluation.harness import EvaluationHarness
from hdleval.toolchain.detect import Toolchain, ToolchainMissingError, missing_tools

det = sys.modules["hdleval.toolchain.detect"]


def _exp(pnr: bool = False) -> ExperimentConfig:
    return ExperimentConfig(
        name="rt",
        models=[ModelConfig(name="r", provider="reference")],
        prompts=[PromptConfig(name="d")],
        synthesis=SynthesisConfig(place_and_route=pnr),
    )


def test_missing_tools_lists_everything():
    tc = Toolchain(present={"ghdl": False, "yosys": True}, ghdl_plugin=False)
    assert missing_tools(tc, place_and_route=True) == [
        "ghdl",
        "ghdl-yosys-plugin",
        "nextpnr-ice40",
    ]


def test_harness_raises_when_required_and_missing(monkeypatch):
    monkeypatch.setenv("HDLEVAL_REQUIRE_TOOLS", "1")
    monkeypatch.setattr(det, "_CACHE", Toolchain(present={}, ghdl_plugin=False))
    with pytest.raises(ToolchainMissingError):
        EvaluationHarness(_exp())


def test_harness_degrades_when_not_required(monkeypatch):
    monkeypatch.delenv("HDLEVAL_REQUIRE_TOOLS", raising=False)
    monkeypatch.setattr(det, "_CACHE", Toolchain(present={}, ghdl_plugin=False))
    EvaluationHarness(_exp())  # no exception
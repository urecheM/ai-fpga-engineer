"""Typed configuration schema.

These dataclasses are intentionally free of behaviour; they are the declarative
surface that experiments are written against. Validation lives in
:func:`validate` methods that raise :class:`ConfigError`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ConfigError(ValueError):
    """Raised when a configuration file is structurally invalid."""


@dataclass(frozen=True)
class ModelConfig:
    """Description of a language-model provider and its inference settings."""

    name: str
    provider: str  # "anthropic" | "reference" | "openai" | "local"
    model_id: str = ""
    temperature: float = 0.0
    max_tokens: int = 4096
    top_p: float = 1.0
    seed: int | None = 0
    system_prompt: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.provider not in {"anthropic", "reference", "synthetic", "rule_based", "openai", "local"}:
            raise ConfigError(f"unknown provider {self.provider!r}")
        if not 0.0 <= self.temperature <= 2.0:
            raise ConfigError("temperature out of range [0, 2]")
        if self.max_tokens <= 0:
            raise ConfigError("max_tokens must be positive")


@dataclass(frozen=True)
class PromptConfig:
    """A named prompt strategy: a system message plus a user template."""

    name: str
    strategy: str = "direct"  # direct | chain_of_thought | few_shot | critique | rag
    system: str = ""
    template: str = "{specification}"
    few_shot_examples: list[dict[str, str]] = field(default_factory=list)
    max_repair_iterations: int = 0

    def validate(self) -> None:
        if "{specification}" not in self.template:
            raise ConfigError("prompt template must reference {specification}")


@dataclass(frozen=True)
class SynthesisConfig:
    name: str = "yosys-ice40"
    backend: str = "yosys"  # yosys | vivado | quartus | stub
    target: str = "ice40"
    clock_ns: float = 10.0
    enabled: bool = True


@dataclass(frozen=True)
class VerificationConfig:
    name: str = "reference-vectors"
    strategy: str = "reference_vectors"  # reference_vectors | formal_equiv | properties
    n_vectors: int = 256
    properties: list[str] = field(default_factory=list)
    enabled: bool = True


@dataclass(frozen=True)
class OptimizationConfig:
    name: str = "baseline"
    objective: str = "none"  # none | area | timing | power | latency | throughput
    max_iterations: int = 0
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchmarkSelector:
    """Selects a slice of the benchmark suite for an experiment."""

    suite_version: str = "v1"
    categories: list[str] = field(default_factory=list)  # empty => all
    difficulty_min: int = 0
    difficulty_max: int = 100
    ids: list[str] = field(default_factory=list)  # empty => all matching


@dataclass(frozen=True)
class ExperimentConfig:
    """Top-level experiment: a cartesian product of models x prompts x benchmarks."""

    name: str
    description: str = ""
    models: list[ModelConfig] = field(default_factory=list)
    prompts: list[PromptConfig] = field(default_factory=list)
    benchmarks: BenchmarkSelector = field(default_factory=BenchmarkSelector)
    synthesis: SynthesisConfig = field(default_factory=SynthesisConfig)
    verification: VerificationConfig = field(default_factory=VerificationConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    trials: int = 1
    seed: int = 0
    tags: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if not self.models:
            raise ConfigError("experiment must define at least one model")
        if not self.prompts:
            raise ConfigError("experiment must define at least one prompt")
        for m in self.models:
            m.validate()
        for p in self.prompts:
            p.validate()
        if self.trials < 1:
            raise ConfigError("trials must be >= 1")

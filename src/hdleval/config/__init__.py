"""Configuration subsystem: typed dataclasses + YAML loading.

Every runtime object (models, prompts, experiments, benchmarks, synthesis,
verification, optimization) is described by a structured config file so that
no execution logic is hard-coded. See :mod:`hdleval.config.schema`.
"""
from __future__ import annotations

from .schema import (
    BenchmarkSelector,
    ExperimentConfig,
    ModelConfig,
    OptimizationConfig,
    PromptConfig,
    SynthesisConfig,
    VerificationConfig,
)
from .loader import load_experiment, load_yaml, resolve_config_dir

__all__ = [
    "BenchmarkSelector",
    "ExperimentConfig",
    "ModelConfig",
    "OptimizationConfig",
    "PromptConfig",
    "SynthesisConfig",
    "VerificationConfig",
    "load_experiment",
    "load_yaml",
    "resolve_config_dir",
]

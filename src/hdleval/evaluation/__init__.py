"""Modular evaluation harness: identical procedure for every model."""
from __future__ import annotations

from .result import BenchmarkResult, StageOutcome
from .harness import EvaluationHarness

__all__ = ["BenchmarkResult", "StageOutcome", "EvaluationHarness"]

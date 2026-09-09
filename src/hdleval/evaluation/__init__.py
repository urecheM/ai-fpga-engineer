"""Modular evaluation harness: identical procedure for every model."""

from __future__ import annotations

from .harness import EvaluationHarness
from .result import BenchmarkResult, StageOutcome

__all__ = ["BenchmarkResult", "EvaluationHarness", "StageOutcome"]

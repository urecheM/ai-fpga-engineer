"""Benchmark suite: structured metadata, loading, and difficulty scoring."""

from __future__ import annotations

from .difficulty import difficulty_score
from .loader import benchmarks_root, load_benchmark, load_suite, select
from .schema import Benchmark, ComplexityMetrics

__all__ = [
    "Benchmark",
    "ComplexityMetrics",
    "benchmarks_root",
    "difficulty_score",
    "load_benchmark",
    "load_suite",
    "select",
]

"""Benchmark suite: structured metadata, loading, and difficulty scoring."""
from __future__ import annotations

from .schema import Benchmark, ComplexityMetrics
from .loader import benchmarks_root, load_benchmark, load_suite, select
from .difficulty import difficulty_score

__all__ = [
    "Benchmark",
    "ComplexityMetrics",
    "benchmarks_root",
    "load_benchmark",
    "load_suite",
    "select",
    "difficulty_score",
]

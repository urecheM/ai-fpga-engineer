"""Objective difficulty scoring.

The score is a transparent weighted sum of complexity dimensions, normalised to
0-100 and bucketed into tiers. Weights are documented in
``docs/evaluation-methodology.md`` and are fixed per suite version for
reproducibility.
"""

from __future__ import annotations

from .schema import ComplexityMetrics

_WEIGHTS = {
    "state_complexity": 3.0,
    "arithmetic_complexity": 2.5,
    "concurrency": 4.0,
    "hierarchy_depth": 3.5,
    "timing_constraints": 2.0,
    "interface_count": 1.0,
    "control_complexity": 2.5,
}

# scaling divisor so a "hard" design lands near 100
_SCALE = 1.6


def difficulty_score(c: ComplexityMetrics) -> int:
    raw = (
        c.state_complexity * _WEIGHTS["state_complexity"]
        + c.arithmetic_complexity * _WEIGHTS["arithmetic_complexity"]
        + c.concurrency * _WEIGHTS["concurrency"]
        + (c.hierarchy_depth - 1) * _WEIGHTS["hierarchy_depth"]
        + c.timing_constraints * _WEIGHTS["timing_constraints"]
        + c.interface_count * _WEIGHTS["interface_count"]
        + c.control_complexity * _WEIGHTS["control_complexity"]
    )
    return int(max(0, min(100, round(raw * _SCALE))))


def difficulty_tier(score: int) -> str:
    if score < 20:
        return "trivial"
    if score < 40:
        return "easy"
    if score < 60:
        return "moderate"
    if score < 80:
        return "hard"
    return "expert"

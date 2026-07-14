"""Objective functions and Pareto-frontier computation for design tradeoffs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Objective(str, Enum):
    AREA = "area"
    TIMING = "timing"
    POWER = "power"
    LATENCY = "latency"
    THROUGHPUT = "throughput"


@dataclass(frozen=True)
class DesignPoint:
    name: str
    area: float  # lower better (LUTs+FFs)
    fmax: float  # higher better
    latency: float  # lower better (cycles)


def score_design(point: DesignPoint, objective: Objective) -> float:
    if objective == Objective.AREA:
        return -point.area
    if objective == Objective.TIMING:
        return point.fmax
    if objective == Objective.LATENCY:
        return -point.latency
    if objective == Objective.THROUGHPUT:
        return point.fmax / max(1.0, point.latency)
    return 0.0


def pareto_frontier(points: list[DesignPoint]) -> list[DesignPoint]:
    """Return non-dominated points minimising (area, latency) & maximising fmax."""
    front: list[DesignPoint] = []
    for p in points:
        dominated = False
        for q in points:
            if q is p:
                continue
            if (
                q.area <= p.area
                and q.latency <= p.latency
                and q.fmax >= p.fmax
                and (q.area < p.area or q.latency < p.latency or q.fmax > p.fmax)
            ):
                dominated = True
                break
        if not dominated:
            front.append(p)
    return front

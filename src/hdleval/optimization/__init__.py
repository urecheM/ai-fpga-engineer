"""Multi-objective optimization: area/power/timing/latency/throughput + Pareto."""
from __future__ import annotations

from .objectives import Objective, pareto_frontier, score_design

__all__ = ["Objective", "pareto_frontier", "score_design"]

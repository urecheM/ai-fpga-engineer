from __future__ import annotations

from hdleval.optimization.objectives import DesignPoint, Objective, pareto_frontier, score_design


def test_objectives_scoring():
    p = DesignPoint("p", area=100, fmax=200, latency=5)
    assert score_design(p, Objective.AREA) == -100
    assert score_design(p, Objective.LATENCY) == -5
    assert score_design(p, Objective.THROUGHPUT) == 200 / 5
    assert score_design(p, Objective.POWER) == 0.0


def test_pareto_excludes_dominated():
    pts = [DesignPoint("a", 100, 200, 5), DesignPoint("dom", 200, 100, 10)]
    front = pareto_frontier(pts)
    names = {p.name for p in front}
    assert "a" in names and "dom" not in names

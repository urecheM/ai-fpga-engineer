from __future__ import annotations

from hdleval.leaderboard.aggregate import build_leaderboard, wilson_interval


def test_wilson_bounds():
    lo, hi = wilson_interval(5, 10)
    assert 0 <= lo <= 0.5 <= hi <= 1
    assert wilson_interval(0, 0) == (0.0, 0.0)


def test_build_leaderboard_counts():
    records = [
        {"model": "m", "prompt": "p", "benchmark": "b1", "passed": True,
         "failure_class": "none", "metrics": {}, "retry_history": []},
        {"model": "m", "prompt": "p", "benchmark": "b1", "passed": False,
         "failure_class": "syntax_error", "metrics": {}, "retry_history": []},
    ]
    meta = {"b1": {"category": "arithmetic", "estimated_difficulty": 10}}
    lb = build_leaderboard(records, meta)
    assert lb.overall[0]["n"] == 2
    assert lb.overall[0]["pass_rate"] == 0.5
    assert "arithmetic" in lb.by_category

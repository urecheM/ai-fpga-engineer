from __future__ import annotations

from hdleval.benchmarks.difficulty import difficulty_score, difficulty_tier
from hdleval.benchmarks.loader import reference_hdl, select
from hdleval.benchmarks.schema import ComplexityMetrics
from hdleval.config.schema import BenchmarkSelector


def test_difficulty_monotonic():
    low = ComplexityMetrics(state_complexity=1, interface_count=2)
    high = ComplexityMetrics(state_complexity=6, concurrency=2, hierarchy_depth=3,
                             control_complexity=6, interface_count=8)
    assert difficulty_score(low) < difficulty_score(high)
    assert 0 <= difficulty_score(high) <= 100


def test_tiers():
    assert difficulty_tier(5) == "trivial"
    assert difficulty_tier(85) == "expert"


def test_suite_nonempty_and_categories(suite):
    assert len(suite) >= 15
    cats = {b.category for b in suite}
    assert {"arithmetic", "fsm", "communication", "memory",
            "processor", "dsp", "control"} <= cats


def test_every_benchmark_has_reference(suite):
    for b in suite:
        assert reference_hdl(b).strip(), f"{b.id} missing reference"


def test_selector_filters(suite):
    sel = BenchmarkSelector(categories=["arithmetic"])
    chosen = select(suite, sel)
    assert chosen and all(b.category == "arithmetic" for b in chosen)

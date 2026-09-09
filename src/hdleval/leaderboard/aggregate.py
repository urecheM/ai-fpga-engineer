"""Aggregate records into leaderboards with confidence measures.

Success rates are reported with Wilson score 95% confidence intervals so that
comparisons across models account for sample size — essential when the suite is
small. Category- and difficulty-tier breakdowns are produced from the same rows.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (round(max(0.0, centre - margin), 4), round(min(1.0, centre + margin), 4))


@dataclass
class ModelStats:
    model: str
    prompt: str
    n: int = 0
    passed: int = 0
    compile_ok: int = 0
    synth_ok: int = 0
    sim_ok: int = 0
    total_latency: float = 0.0
    total_tokens: int = 0
    total_retries: int = 0
    failure_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def row(self) -> dict[str, Any]:
        lo, hi = wilson_interval(self.passed, self.n)
        return {
            "model": self.model,
            "prompt": self.prompt,
            "n": self.n,
            "pass_rate": round(self.passed / self.n, 4) if self.n else 0.0,
            "pass_ci95": [lo, hi],
            "compile_rate": round(self.compile_ok / self.n, 4) if self.n else 0.0,
            "synth_rate": round(self.synth_ok / self.n, 4) if self.n else 0.0,
            "sim_rate": round(self.sim_ok / self.n, 4) if self.n else 0.0,
            "avg_latency_s": round(self.total_latency / self.n, 4) if self.n else 0.0,
            "avg_tokens": round(self.total_tokens / self.n, 1) if self.n else 0.0,
            "avg_retries": round(self.total_retries / self.n, 3) if self.n else 0.0,
            "failures": dict(self.failure_counts),
        }


@dataclass
class Leaderboard:
    overall: list[dict[str, Any]] = field(default_factory=list)
    by_category: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    by_difficulty: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall,
            "by_category": self.by_category,
            "by_difficulty": self.by_difficulty,
        }


def _tier(difficulty: int) -> str:
    return ["trivial", "easy", "moderate", "hard", "expert"][min(4, difficulty // 20)]


def _accumulate(records: list[dict[str, Any]], keyfn) -> dict[Any, ModelStats]:
    stats: dict[Any, ModelStats] = {}
    for r in records:
        key = keyfn(r)
        st = stats.setdefault(key, ModelStats(model=r["model"], prompt=r["prompt"]))
        st.n += 1
        st.passed += int(r["passed"])
        metrics = r.get("metrics", {})
        st.total_latency += float(metrics.get("inference_latency_s", 0.0))
        st.total_tokens += int(metrics.get("prompt_tokens", 0)) + int(
            metrics.get("completion_tokens", 0)
        )
        st.total_retries += int((r.get("retry_history", []) and len(r["retry_history"])) or 0)
        st.failure_counts[r.get("failure_class", "none")] += 1
        # stage-derived counters live in metrics for records; recompute leniently
        if r.get("failure_class") not in ("compilation_error", "no_code_generated"):
            st.compile_ok += 1
        res = metrics.get("resources", {})
        if res.get("available"):
            st.synth_ok += 1
        if r.get("passed"):
            st.sim_ok += 1
    return stats


def build_leaderboard(
    records: list[dict[str, Any]], benchmark_meta: dict[str, dict]
) -> Leaderboard:
    def mp(r: dict) -> tuple[str, str]:
        return (r["model"], r["prompt"])

    overall = [
        s.row()
        for s in sorted(
            _accumulate(records, mp).values(), key=lambda s: -(s.passed / s.n if s.n else 0)
        )
    ]

    by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    cats = {benchmark_meta.get(r["benchmark"], {}).get("category", "unknown") for r in records}
    for c in sorted(cats):
        subset = [r for r in records if benchmark_meta.get(r["benchmark"], {}).get("category") == c]
        by_cat[c] = [s.row() for s in _accumulate(subset, mp).values()]

    by_diff: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        r["_tier"] = _tier(benchmark_meta.get(r["benchmark"], {}).get("estimated_difficulty", 0))
    for t in ["trivial", "easy", "moderate", "hard", "expert"]:
        subset = [r for r in records if r.get("_tier") == t]
        if subset:
            by_diff[t] = [s.row() for s in _accumulate(subset, mp).values()]

    return Leaderboard(overall=overall, by_category=dict(by_cat), by_difficulty=dict(by_diff))

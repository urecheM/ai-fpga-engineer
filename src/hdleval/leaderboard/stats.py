from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Hashable, Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class McNemarResult:
    both_pass: int
    a_only: int
    b_only: int
    both_fail: int
    p_value: float


def mcnemar_exact(pairs: Iterable[tuple[bool, bool]]) -> McNemarResult:
    """Two-sided exact McNemar test on (a_passed, b_passed) pairs."""
    n11 = n10 = n01 = n00 = 0
    for a, b in pairs:
        if a and b:
            n11 += 1
        elif a:
            n10 += 1
        elif b:
            n01 += 1
        else:
            n00 += 1
    n = n10 + n01
    if n == 0:
        p = 1.0
    else:
        k = min(n10, n01)
        p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n)
    return McNemarResult(n11, n10, n01, n00, p)


@dataclass(frozen=True)
class BootstrapResult:
    mean_diff: float
    ci_low: float
    ci_high: float
    n_clusters: int
    n_resamples: int


def paired_bootstrap(
    rows: Iterable[tuple[Hashable, float, float]],
    *,
    n_resamples: int = 10_000,
    seed: int = 0,
    alpha: float = 0.05,
) -> BootstrapResult:
    """Percentile CI for mean(a)-mean(b), resampling clusters with replacement.

    ``rows`` are ``(cluster, a_value, b_value)``; the cluster is normally the
    benchmark id, so all trials of a benchmark move together.
    """
    by_cluster: dict[Hashable, list[float]] = defaultdict(list)
    for cluster, a, b in rows:
        by_cluster[cluster].append(float(a) - float(b))
    clusters = list(by_cluster.values())
    if not clusters:
        return BootstrapResult(0.0, 0.0, 0.0, 0, 0)

    def mean_of(sample: list[list[float]]) -> float:
        vals = [d for c in sample for d in c]
        return sum(vals) / len(vals)

    observed = mean_of(clusters)
    rng = random.Random(seed)
    k = len(clusters)
    stats = sorted(
        mean_of([clusters[rng.randrange(k)] for _ in range(k)]) for _ in range(n_resamples)
    )
    lo = stats[int((alpha / 2) * n_resamples)]
    hi = stats[min(n_resamples - 1, int((1 - alpha / 2) * n_resamples))]
    return BootstrapResult(round(observed, 4), round(lo, 4), round(hi, 4), k, n_resamples)


def pair_records(
    records: list[dict], model_a: str, model_b: str, prompt: str | None = None
) -> list[tuple[str, dict, dict]]:
    """Match runs of two models on (benchmark, prompt, trial)."""
    idx: dict[tuple, dict] = {}
    for r in records:
        if r["model"] == model_b and (prompt is None or r["prompt"] == prompt):
            idx[(r["benchmark"], r["prompt"], r["trial"])] = r
    out = []
    for r in records:
        if r["model"] == model_a and (prompt is None or r["prompt"] == prompt):
            other = idx.get((r["benchmark"], r["prompt"], r["trial"]))
            if other is not None:
                out.append((r["benchmark"], r, other))
    return out

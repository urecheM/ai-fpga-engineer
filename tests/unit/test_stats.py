from __future__ import annotations

import pytest

from hdleval.leaderboard.stats import mcnemar_exact, paired_bootstrap


def test_mcnemar_no_discordant_pairs():
    assert mcnemar_exact([(True, True), (False, False)]).p_value == 1.0


def test_mcnemar_matches_statsmodels():
    sm = pytest.importorskip("statsmodels.stats.contingency_tables")
    pairs = [(True, False)] * 9 + [(False, True)] * 2 + [(True, True)] * 30 + [(False, False)] * 13
    ours = mcnemar_exact(pairs)
    ref = sm.mcnemar([[30, 9], [2, 13]], exact=True)
    assert ours.a_only == 9 and ours.b_only == 2
    assert ours.p_value == pytest.approx(ref.pvalue)


def test_paired_bootstrap_ci_contains_observed_and_is_seeded():
    rows = [(f"b{i}", i % 3 != 0, i % 5 == 0) for i in range(30)]
    a = paired_bootstrap(rows, n_resamples=2000, seed=1)
    b = paired_bootstrap(rows, n_resamples=2000, seed=1)
    assert a == b
    assert a.ci_low <= a.mean_diff <= a.ci_high
    assert a.n_clusters == 30

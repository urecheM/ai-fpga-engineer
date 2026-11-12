#!/usr/bin/env python3
#McNemar + paired bootstrap
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from hdleval.leaderboard.stats import mcnemar_exact, pair_records, paired_bootstrap
from hdleval.registry.database import ExperimentDB
from static_vs_toolchain_gap import latest_runs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--db", default=str(ROOT / "experiments" / "registry.sqlite"))
    ap.add_argument("--out", default=str(ROOT / "results" / "reports"))
    ap.add_argument("--resamples", type=int, default=10_000)
    args = ap.parse_args()

    db = ExperimentDB(args.db)
    recs = latest_runs(db.all_records(args.experiment))
    db.close()
    models = sorted({r["model"] for r in recs})
    lines = [
        f"# Paired comparisons: {args.experiment}\n",
        "Runs matched on (benchmark, prompt, trial). McNemar is exact and two-sided; "
        "bootstrap CIs resample benchmarks (clusters).\n",
        "| A | B | n pairs | A only | B only | McNemar p | pass-rate diff A-B [95% CI] "
        "| latency diff s [95% CI] |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for a, b in itertools.combinations(models, 2):
        pairs = pair_records(recs, a, b)
        if not pairs:
            continue
        mc = mcnemar_exact((ra["passed"], rb["passed"]) for _, ra, rb in pairs)
        pr = paired_bootstrap(
            ((bm, ra["passed"], rb["passed"]) for bm, ra, rb in pairs),
            n_resamples=args.resamples,
        )
        lat = paired_bootstrap(
            (
                (
                    bm,
                    ra.get("metrics", {}).get("inference_latency_s", 0.0),
                    rb.get("metrics", {}).get("inference_latency_s", 0.0),
                )
                for bm, ra, rb in pairs
            ),
            n_resamples=args.resamples,
        )
        lines.append(
            f"| {a} | {b} | {len(pairs)} | {mc.a_only} | {mc.b_only} | {mc.p_value:.4g} "
            f"| {pr.mean_diff:+.3f} [{pr.ci_low:+.3f}, {pr.ci_high:+.3f}] "
            f"| {lat.mean_diff:+.3f} [{lat.ci_low:+.3f}, {lat.ci_high:+.3f}] |"
        )
    text = "\n".join(lines) + "\n"
    out = Path(args.out) / f"{args.experiment}_paired.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
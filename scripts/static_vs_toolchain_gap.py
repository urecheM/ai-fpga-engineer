#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hdleval.leaderboard.aggregate import wilson_interval
from hdleval.leaderboard.stats import mcnemar_exact
from hdleval.registry.database import ExperimentDB


def latest_runs(records: list[dict]) -> list[dict]:
    """Keep the most recent record per (model, prompt, benchmark, trial)."""
    best: dict[tuple, dict] = {}
    for r in records:
        k = (r["model"], r["prompt"], r["benchmark"], r["trial"])
        if k not in best or r.get("started_at", 0) >= best[k].get("started_at", 0):
            best[k] = r
    return list(best.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--db", default=str(ROOT / "experiments" / "registry.sqlite"))
    ap.add_argument("--out", default=str(ROOT / "results" / "reports"))
    args = ap.parse_args()

    db = ExperimentDB(args.db)
    recs = latest_runs(db.all_records(args.experiment))
    db.close()
    recs = [r for r in recs if "static_pass" in r.get("metrics", {})]
    if not recs:
        print("no records with metrics.static_pass; re-run the experiment", file=sys.stderr)
        return 1

    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in recs:
        by_model[r["model"]].append(r)

    lines = [
        f"# Static-only vs toolchain verdicts: {args.experiment}\n",
        "| model | n | static pass | 95% CI | toolchain pass | 95% CI | gap (pp) "
        "| static-only false accepts | McNemar p |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for model, rs in sorted(by_model.items()):
        n = len(rs)
        s = sum(bool(r["metrics"]["static_pass"]) for r in rs)
        t = sum(bool(r["passed"]) for r in rs)
        false_accepts = sum(bool(r["metrics"]["static_pass"]) and not r["passed"] for r in rs)
        slo, shi = wilson_interval(s, n)
        tlo, thi = wilson_interval(t, n)
        mc = mcnemar_exact((bool(r["metrics"]["static_pass"]), bool(r["passed"])) for r in rs)
        lines.append(
            f"| {model} | {n} | {s / n:.3f} | [{slo:.3f}, {shi:.3f}] | {t / n:.3f} "
            f"| [{tlo:.3f}, {thi:.3f}] | {100 * (s - t) / n:+.1f} | {false_accepts} | {mc.p_value:.3g} |"
        )
    text = "\n".join(lines) + "\n"
    out = Path(args.out) / f"{args.experiment}_static_gap.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
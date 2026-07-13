"""Command-line interface for the hdleval research platform.

Subcommands:
    list-benchmarks        show the versioned benchmark suite + difficulty
    run <experiment.yaml>  execute an experiment and populate the registry
    report <experiment>    regenerate reports/figures from the registry
    toolchain              print detected HDL toolchain status
    version                print the platform version
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .benchmarks.difficulty import difficulty_tier
from .benchmarks.loader import load_suite
from .config.loader import load_experiment
from .leaderboard.aggregate import build_leaderboard
from .reporting.figures import write_all_figures
from .reporting.reports import write_all_reports
from .toolchain import detect


def _cmd_list_benchmarks(args: argparse.Namespace) -> int:
    suite = load_suite(args.suite)
    for b in suite:
        print(
            f"{b.id:22s} {b.category:14s} diff={b.estimated_difficulty:3d} "
            f"({difficulty_tier(b.estimated_difficulty)})  {b.title}"
        )
    print(f"\n{len(suite)} benchmarks in suite {args.suite}")
    return 0


def _cmd_toolchain(_: argparse.Namespace) -> int:
    print(detect().summary())
    return 0


def _preflight(exp) -> None:
    """Warn (do not fail) when an experiment references providers whose runtime
    prerequisites are absent, so a real-model run gives an actionable message."""
    import os

    for m in exp.models:
        if m.provider == "anthropic":
            has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
            try:
                import anthropic  # noqa: F401

                has_sdk = True
            except Exception:
                has_sdk = False
            if not (has_key and has_sdk):
                miss = []
                if not has_key:
                    miss.append("ANTHROPIC_API_KEY")
                if not has_sdk:
                    miss.append("the `anthropic` SDK (pip install 'hdleval[anthropic]')")
                print(
                    f"[preflight] model '{m.name}' uses the anthropic provider but "
                    f"{' and '.join(miss)} {'is' if len(miss) == 1 else 'are'} missing; "
                    "its benchmarks will be recorded as generation failures. "
                    "Set the key / install the SDK for a real run."
                )


def _cmd_run(args: argparse.Namespace) -> int:
    from .evaluation.runner import run_experiment

    exp = load_experiment(args.experiment)
    _preflight(exp)
    results, records = run_experiment(
        exp, out_dir=args.out, db_path=args.db, benchmarks_root=args.benchmarks
    )
    suite = {b.id: b.to_dict() for b in load_suite(exp.benchmarks.suite_version, args.benchmarks)}
    lb = build_leaderboard([r.to_dict() for r in records], suite)
    written = write_all_reports([r.to_dict() for r in records], lb, args.out, exp.name)
    figs = write_all_figures(
        lb.to_dict(), [r.to_dict() for r in records], str(Path(args.out) / "figures")
    )
    passed = sum(1 for r in results if r.passed)
    print(f"ran {len(results)} evaluations · {passed} passed")
    print(json.dumps({**written, **figs}, indent=2))
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    from .registry.database import ExperimentDB

    db = ExperimentDB(args.db)
    records = db.all_records(args.experiment)
    db.close()
    if not records:
        print(f"no records for experiment {args.experiment!r}", file=sys.stderr)
        return 1
    suite = {b.id: b.to_dict() for b in load_suite("v1", args.benchmarks)}
    lb = build_leaderboard(records, suite)
    write_all_reports(records, lb, args.out, args.experiment)
    write_all_figures(lb.to_dict(), records, str(Path(args.out) / "figures"))
    print(f"regenerated reports for {args.experiment} ({len(records)} records)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hdleval", description="LLM-Assisted Hardware Design Research Platform"
    )
    p.add_argument("--version", action="version", version=f"hdleval {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    lb = sub.add_parser("list-benchmarks")
    lb.add_argument("--suite", default="v1")
    lb.set_defaults(func=_cmd_list_benchmarks)

    tc = sub.add_parser("toolchain")
    tc.set_defaults(func=_cmd_toolchain)

    r = sub.add_parser("run")
    r.add_argument("experiment")
    r.add_argument("--out", default="results")
    r.add_argument("--db", default="experiments/registry.sqlite")
    r.add_argument("--benchmarks", default=None)
    r.set_defaults(func=_cmd_run)

    rp = sub.add_parser("report")
    rp.add_argument("experiment")
    rp.add_argument("--out", default="results")
    rp.add_argument("--db", default="experiments/registry.sqlite")
    rp.add_argument("--benchmarks", default=None)
    rp.set_defaults(func=_cmd_report)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""One-command reproduction of every figure, table, report and artifact.

    python reproduce.py [--experiment configs/experiments/baseline.yaml]

Steps (each idempotent):
  1. (re)build the versioned benchmark suite
  2. run the experiment through the evaluation harness -> experiment registry
  3. regenerate leaderboards, reports (JSON/CSV/MD/HTML) and figures
  4. regenerate publication tables/figures and the research website data

Nothing downstream is hand-edited; this script is the single source of truth
for reproducibility. In an environment with GHDL + Yosys installed (see the
Dockerfile) the compile/synthesis/simulation stages run for real; otherwise
they are recorded as 'skipped' and functional correctness falls back to the
documented static signal.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


def _run(mod_args: list[str]) -> None:
    print(f"\n$ python -m {' '.join(mod_args)}")
    subprocess.check_call([sys.executable, "-m", *mod_args], cwd=ROOT,
                          env={"PYTHONPATH": str(SRC), "PATH": _path()})


def _path() -> str:
    import os
    return os.environ.get("PATH", "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", default="configs/experiments/baseline.yaml")
    ap.add_argument("--out", default="results")
    ap.add_argument("--db", default="experiments/registry.sqlite")
    args = ap.parse_args()

    import os
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC)

    print("== [1/4] build benchmark suite ==")
    subprocess.check_call([sys.executable, "scripts/build_benchmarks.py"], cwd=ROOT, env=env)

    print("== [2/4] run experiment ==")
    subprocess.check_call(
        [sys.executable, "-m", "hdleval.cli", "run", args.experiment,
         "--out", args.out, "--db", args.db], cwd=ROOT, env=env)

    print("== [3/4] generate publication artifacts ==")
    subprocess.check_call([sys.executable, "scripts/generate_publication.py"], cwd=ROOT, env=env)

    print("== [4/4] generate website data ==")
    subprocess.check_call([sys.executable, "scripts/generate_website.py"], cwd=ROOT, env=env)

    print("\nReproduction complete. See results/, publication/ and website/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

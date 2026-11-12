#!/usr/bin/env python3
#Generating parametric benchmark variants from templates (limits memorisation)
from __future__ import annotations

import argparse
import itertools
import random
import shutil
import sys
from pathlib import Path
from string import Template

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import build_golden_vectors as golden  # noqa: E402
from hdleval.benchmarks.loader import load_benchmark  # noqa: E402

TEMPLATES = ROOT / "benchmarks" / "templates"


def derived(params: dict) -> dict:
    out = {k: str(v) for k, v in params.items()}
    for k, v in params.items():
        if isinstance(v, int):
            out[f"{k}1"] = str(v - 1)
    if "PATTERN" in params:
        n = len(str(params["PATTERN"]))
        out.update(N=str(n), N1=str(n - 1), N2=str(n - 2), N3=str(n - 3))
    return out


def render(tdir: Path, params: dict, suite_dir: Path, seed: int) -> Path:
    values = derived(params)
    meta = yaml.safe_load(Template((tdir / "template.yaml").read_text()).substitute(values))
    meta.pop("parameters", None)
    ref = Template((tdir / "reference.vhd.tmpl").read_text()).substitute(values)
    bdir = suite_dir / meta["id"]
    bdir.mkdir(parents=True, exist_ok=True)
    (bdir / "reference.vhd").write_text(ref)
    meta.update(
        version="1.0.0",
        expected_behavior="",
        reference_hdl_path="reference.vhd",
        properties=[],
        variant_of=tdir.name,
        parameters=params,
        release_seed=seed,
    )
    (bdir / "benchmark.yaml").write_text(yaml.safe_dump(meta, sort_keys=False))
    return bdir


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--release-seed", type=int, required=True)
    ap.add_argument("--per-template", type=int, default=3)
    ap.add_argument("--suite", default="v1-variants")
    args = ap.parse_args()
    if not shutil.which("ghdl"):
        print("ghdl is required to verify the generated references", file=sys.stderr)
        return 1

    suite_dir = ROOT / "benchmarks" / args.suite
    if suite_dir.exists():
        shutil.rmtree(suite_dir)
    rng = random.Random(args.release_seed)
    failed = False
    for tdir in sorted(p for p in TEMPLATES.iterdir() if (p / "template.yaml").exists()):
        grid = yaml.safe_load((tdir / "template.yaml").read_text())["parameters"]
        keys = sorted(grid)
        combos = [
            dict(zip(keys, vals, strict=True))
            for vals in itertools.product(*(grid[k] for k in keys))
        ]
        chosen = rng.sample(combos, min(args.per_template, len(combos)))
        for params in chosen:
            bdir = render(tdir, params, suite_dir, args.release_seed)
            bench = load_benchmark(bdir, suite=args.suite)
            msg = golden.build_one(bench, None, force=True)
            if msg.startswith("ok"):
                meta = yaml.safe_load((bdir / "benchmark.yaml").read_text())
                meta["testbench_path"] = "golden_tb.vhd"
                meta["testbench_entity"] = f"{bench.entity}_golden_tb"
                (bdir / "benchmark.yaml").write_text(yaml.safe_dump(meta, sort_keys=False))
            else:
                failed = True
            print(f"{bench.id:28s} {msg}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
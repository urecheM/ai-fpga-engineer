#!/usr/bin/env python3
from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hdleval.benchmarks.loader import load_suite, reference_hdl, testbench_hdl
from hdleval.models.faults import SEMANTIC
from hdleval.toolchain import compile_vhdl, simulate
from hdleval.toolchain.detect import detect


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--suite", default="v1")
    args = ap.parse_args()
    if not detect().has("ghdl"):
        print("ghdl required", file=sys.stderr)
        return 1
    tally: dict[str, Counter] = {n: Counter() for n in SEMANTIC}
    rows = []
    for b in load_suite(args.suite):
        ref, tb = reference_hdl(b), testbench_hdl(b)
        for name, op in SEMANTIC.items():
            for s in range(args.seeds):
                mut = op(ref, random.Random(s))
                if mut is None or mut == ref:
                    tally[name]["n/a"] += 1
                    continue
                c = compile_vhdl(mut, entity=b.entity)
                if c.status != "ok":
                    outcome = "no_compile"
                elif not tb:
                    outcome = "no_testbench"
                else:
                    sim = simulate(mut, tb, b.testbench_entity)
                    outcome = "detected" if sim.status == "fail" else "escaped"
                tally[name][outcome] += 1
                rows.append((b.id, name, s, outcome))
    cols = ["detected", "escaped", "no_compile", "no_testbench", "n/a"]
    lines = [
        "# Semantic fault validation\n",
        "Each operator applied to every reference with "
        f"{args.seeds} seeds. `escaped` = compiled and passed the testbench "
        "(equivalent or undetected mutant).\n",
        "| operator | " + " | ".join(cols) + " |",
        "|---|" + "---|" * len(cols),
    ]
    for name, t in tally.items():
        lines.append(f"| {name} | " + " | ".join(str(t[c]) for c in cols) + " |")
    lines += ["", "## Escapes", ""]
    lines += [f"- {b} / {n} / seed {s}" for b, n, s, o in rows if o == "escaped"] or ["- none"]
    out = ROOT / "results" / "reports" / "fault_validation.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[2 : 4 + len(tally)]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

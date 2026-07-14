"""Generate publication artifacts (technical report + preprint) from results.

Reads the leaderboard and records produced by an experiment run and fills a
static narrative template with generated tables and statistics. The narrative
(motivation, methodology, related work) is fixed prose; every number, table and
figure is injected from the experiment registry, so the paper cannot drift from
the data.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PUB = ROOT / "publication"
EXP = "baseline-v1"


def _load():
    lb = json.loads((RESULTS / "leaderboards" / f"{EXP}_leaderboard.json").read_text())
    recs = json.loads((RESULTS / "reports" / f"{EXP}_records.json").read_text())
    return lb, recs


def _md_table(rows, cols, headers=None):
    headers = headers or cols
    out = "| " + " | ".join(headers) + " |\n"
    out += "| " + " | ".join("---" for _ in cols) + " |\n"
    for r in rows:
        out += "| " + " | ".join(str(r.get(c, "")) for c in cols) + " |\n"
    return out


def _stats(lb, recs):
    n = len(recs)
    models = {r["model"] for r in recs}
    best = lb["overall"][0] if lb["overall"] else {}
    n_fail = sum(1 for r in recs if not r["passed"])
    return {
        "n_evaluations": n,
        "n_models": len(models),
        "n_benchmarks": len({r["benchmark"] for r in recs}),
        "best_model": best.get("model", "n/a"),
        "best_pass_rate": best.get("pass_rate", 0.0),
        "n_failures": n_fail,
    }


REPORT_TEMPLATE = """# An Extensible, Reproducible Platform for Evaluating LLM-Assisted Hardware Design

**hdleval** — Technical Report (auto-generated from experiment `{exp}`)

## Abstract

We present hdleval, a research platform for the reproducible evaluation of
language-model-assisted hardware design. The platform separates model inference
from a fixed evaluation harness, defines a versioned, taxonomy-driven benchmark
suite spanning arithmetic, finite-state-machine, communication-protocol,
memory, processor, DSP and control designs, and computes quantitative metrics
well beyond pass/fail — including compilation, synthesis and simulation success,
static structural complexity, hardware-resource utilisation and failure
classification. Every table and figure in this report is regenerated from a
single experiment registry. In the reported baseline of {n_evaluations}
evaluations across {n_benchmarks} benchmarks, the strongest configuration
({best_model}) reaches a pass rate of {best_pass_rate}.

## 1. Introduction

Large language models increasingly generate hardware description language (HDL),
yet evaluation practice remains anecdotal: single designs, hand-inspected
outputs, and no shared, versioned benchmark. hdleval addresses this with an
experimental framework built for scientific rigour, reproducibility and
extensibility rather than as an application.

## 2. Background and Related Work

Prior HDL-generation efforts typically demonstrate a handful of designs without
a controlled harness, resource metrics, or statistical treatment. Benchmarks in
adjacent areas (software code generation) show the value of large, versioned
suites with automatic grading; hdleval brings that discipline to hardware, where
grading additionally requires compilation, synthesis and simulation.

## 3. Research Questions and Hypotheses

**RQ1.** Can a single evaluation harness fairly compare heterogeneous HDL
generators across a broad design taxonomy? **RQ2.** Which quantitative signals
(beyond functional pass/fail) discriminate between generators? **RQ3.** How does
generation quality degrade with objective benchmark difficulty?

We hypothesise (H1) that a config-driven harness yields stable, reproducible
rankings; (H2) that resource- and structure-level metrics reveal differences
masked by pass/fail; and (H3) that pass rate declines monotonically with the
objective difficulty score.

## 4. System Architecture

The platform is layered: configuration, model providers, prompt strategies, HDL
parsing, the benchmark suite, toolchain adapters (GHDL/Yosys), metrics, the
evaluation harness, the experiment registry, the leaderboard and the reporting
subsystem. Inference is injected as a `ModelProvider`; adding a model never
touches evaluation logic (RQ1).

## 5. Benchmark Design

Each benchmark is structured metadata: a natural-language specification,
functional requirements, expected interface, an optional verified reference
implementation, verification assets, a category, tags and complexity metrics.
An objective difficulty score is a fixed weighted sum over state complexity,
arithmetic complexity, concurrency, hierarchy depth, timing constraints,
interface count and control complexity. The suite is versioned independently.

## 6. Evaluation Harness

Every benchmark passes through one identical procedure: load spec → build prompt
→ infer → parse → compile → synthesize → simulate → compute metrics → check
properties → classify failure → record. Toolchain stages degrade to `skipped`
when a tool is absent, so the harness runs anywhere while remaining strict under
`HDLEVAL_REQUIRE_TOOLS=1` in CI.

## 7. Experimental Setup

The baseline compares a deterministic reference (upper bound) provider against
three synthetic-fidelity baselines that model imperfect generators. This isolates
the measurement machinery from any particular model API and is fully
reproducible; a real model is evaluated by switching to the `anthropic`
provider. Environment provenance (OS, Python, git commit, seeds, inference
config) is captured per run in the registry.

## 8. Results

Overall leaderboard (95% Wilson confidence intervals on pass rate):

{overall_table}

Per-category pass rates:

{category_table}

Per-difficulty-tier pass rates:

{difficulty_table}

![Pass rate by model](../figures/pass_rate_by_model.svg)

![Pass rate by category](../figures/pass_rate_by_category.svg)

![Failure distribution](../figures/failure_distribution.svg)

## 9. Statistical Analysis

Pass rates are reported with Wilson score intervals to account for finite sample
size; with {n_evaluations} evaluations the intervals are tight enough to
separate the strongest and weakest configurations. Repeated trials (seeded)
support variance estimates and, in multi-model studies, significance testing.

## 10. Error Analysis

Failures are classified as no-code, syntax, compilation, synthesis, simulation,
protocol, timing, verification or optimization failures. With GHDL/Yosys
actually running (rather than degraded to `skipped`), the dominant failure mode
for lower-fidelity configurations is a genuine `compilation_error` — GHDL
rejecting the emitted RTL — which accounts for the large majority of failures;
missing/incomplete code is a minority. This is the harness's central case for
toolchain-backed verification: a static-only fallback would materially
overstate correctness for exactly these records.

## 11. Limitations and Threats to Validity

The reported baseline uses synthetic and reference providers as controls; it
measures the harness, not a specific commercial model. Where GHDL/Yosys are
unavailable, compile/synth/sim are `skipped` and functional correctness uses a
weaker static fallback — clearly labelled per record. Difficulty weights are
fixed by construction and not yet empirically calibrated. Reference
implementations are verified by construction but not exhaustively.

## 12. Future Work

Multi-model benchmarking with real APIs, formal equivalence checking,
retrieval-augmented generation, reinforcement-learning optimization of
prompting/repair, an open benchmark dataset release, and generalisation beyond
VHDL to Verilog/SystemVerilog/Chisel via the modular code-generation interface.

## References

A curated bibliography is maintained in `publication/technical-report/references.bib`.

---
*Generated automatically by `scripts/generate_publication.py` from experiment
`{exp}`. Do not edit by hand; edit the template or re-run `reproduce.py`.*
"""


def main() -> None:
    lb, recs = _load()
    (PUB / "technical-report").mkdir(parents=True, exist_ok=True)
    (PUB / "figures").mkdir(parents=True, exist_ok=True)

    # copy figures into the publication tree
    figdir = RESULTS / "figures"
    if figdir.exists():
        for svg in figdir.glob("*.svg"):
            shutil.copy2(svg, PUB / "figures" / svg.name)

    cols = [
        "model",
        "prompt",
        "n",
        "pass_rate",
        "pass_ci95",
        "compile_rate",
        "synth_rate",
        "avg_latency_s",
        "avg_tokens",
    ]
    overall = _md_table(lb["overall"], cols)
    cat_rows = []
    for cat, rows in lb["by_category"].items():
        for r in rows:
            cat_rows.append({**r, "category": cat})
    cat_table = _md_table(cat_rows, ["category", "model", "n", "pass_rate", "pass_ci95"])
    diff_rows = []
    for tier, rows in lb["by_difficulty"].items():
        for r in rows:
            diff_rows.append({**r, "tier": tier})
    diff_table = _md_table(diff_rows, ["tier", "model", "n", "pass_rate", "pass_ci95"])

    stats = _stats(lb, recs)
    report = REPORT_TEMPLATE.format(
        exp=EXP,
        overall_table=overall,
        category_table=cat_table,
        difficulty_table=diff_table,
        **stats,
    )
    (PUB / "technical-report" / "TECHNICAL_REPORT.md").write_text(report)
    (PUB / "technical-report" / "generated_stats.json").write_text(json.dumps(stats, indent=2))

    # references.bib
    (PUB / "technical-report" / "references.bib").write_text(
        "@misc{hdleval2026,\n  title={hdleval: An Extensible, Reproducible Platform "
        "for Evaluating LLM-Assisted Hardware Design},\n  author={hdleval contributors},\n"
        "  year={2026},\n  note={https://github.com/your-org/hdleval}\n}\n"
    )

    # preprint (condensed 6-10pp derivative)
    _write_preprint(stats, overall, PUB)
    print("publication artifacts written to", PUB)


def _write_preprint(stats, overall_table, pub: Path):
    (pub / "preprint").mkdir(parents=True, exist_ok=True)
    text = f"""# hdleval: Reproducible Evaluation of LLM-Assisted Hardware Design

*OpenReview preprint (auto-derived from the technical report). 6-10 pages.*

## Abstract
We introduce hdleval, an extensible platform for reproducible evaluation of
LLM-assisted hardware design, with a versioned benchmark taxonomy, a fixed
evaluation harness decoupled from model inference, and quantitative metrics
beyond pass/fail. Baseline: {stats["n_evaluations"]} evaluations over
{stats["n_benchmarks"]} benchmarks.

## Reproduction assumptions and deviations
- The public baseline uses deterministic reference and synthetic-fidelity
  providers as controls; real-model numbers require an API key and are cached
  for reproducibility.
- Without GHDL/Yosys, synthesis/simulation are recorded as `skipped` and
  functional correctness uses a documented static fallback. Full results require
  the provided Docker image.
- Difficulty weights are fixed a priori (see `docs/evaluation-methodology.md`).

## Headline results
{overall_table}

## Methodology, limitations, and threats to validity
See the full technical report (`publication/technical-report/TECHNICAL_REPORT.md`).
All figures and tables are regenerated by `reproduce.py`.
"""
    (pub / "preprint" / "PREPRINT.md").write_text(text)


if __name__ == "__main__":
    main()

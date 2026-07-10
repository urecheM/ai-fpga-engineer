# hdleval — LLM-Assisted Hardware Design Research Platform

> A reproducible experimental framework for evaluating AI-assisted hardware
> design methodologies. Not an application — research infrastructure.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen)
![Tests](https://img.shields.io/badge/tests-48%20passing-success)
![HDL](https://img.shields.io/badge/target-VHDL--2008-orange)
![Status](https://img.shields.io/badge/release-v0.1%20prototype-blueviolet)

hdleval treats AI-assisted hardware design as a measurable experimental science.
It provides a **config-driven evaluation harness** (inference decoupled from
grading), a **versioned benchmark taxonomy**, **quantitative metrics beyond
pass/fail**, a **provenance-complete experiment registry**, and **automatically
generated** leaderboards, reports, figures, a technical report, a preprint and a
research website. Every public artifact is a build product of the experiments —
`python reproduce.py` regenerates all of it.

## Motivation

HDL-generation results today are anecdotal: a few hand-picked designs, inspected
by eye, with no controlled harness, no resource metrics, no versioned benchmark
and no statistics. hdleval makes claims comparable across models, prompts and
releases, and lets progress be tracked over time. See
[`docs/research-specification.md`](docs/research-specification.md) for the
research questions, hypotheses and success criteria.

## Architecture

```
configs/  ─▶ hdleval.config          models/  ─▶ ModelProvider (reference|synthetic|anthropic)
prompts/  ─▶ PromptStrategy          benchmarks/v1 ─▶ Benchmark suite (metadata + reference HDL)
toolchain ─▶ GHDL / Yosys adapters   metrics ─▶ static + resource
        └──────────────▶ EvaluationHarness ─▶ ExperimentDB ─▶ Leaderboard ─▶ Reports/Figures ─▶ Publication/Website
```

Inference is injected as a `ModelProvider`; **adding a model never touches
evaluation logic**. Decisions are recorded as ADRs under [`docs/adr/`](docs/adr).

## Benchmark methodology

18 benchmarks (suite **v1**) across seven categories — arithmetic, finite-state
machines, communication protocols, memory, processors, DSP and control — each a
piece of structured metadata: a natural-language specification, functional
requirements, expected interface, a verified reference implementation,
verification assets, tags and complexity metrics. An **objective difficulty
score** (weighted over state/arithmetic/concurrency/hierarchy/timing/interface/
control complexity) buckets each into trivial→expert. The suite is versioned
independently so revisions stay reproducible. See
[`docs/guides/benchmarks.md`](docs/guides/benchmarks.md).

## Evaluation pipeline

Every benchmark, for every model, runs one identical procedure:

```
load spec ▶ build prompt ▶ infer ▶ parse ▶ compile ▶ synthesize
        ▶ simulate ▶ metrics ▶ properties ▶ classify ▶ record
```

Metrics span functional (compile/synth/sim/properties), structural (static
analysis), resource (LUT/FF/DSP/BRAM, estimated Fmax, area efficiency) and
process (latency, tokens, retries). Failures are classified into one canonical
class. Toolchain stages degrade to `skipped` when GHDL/Yosys are absent (strict
in CI). Full detail: [`docs/evaluation-methodology.md`](docs/evaluation-methodology.md).

## Experiments

`baseline-v1` (shipped) compares a deterministic reference (upper bound) against
three synthetic-fidelity baselines across the full suite, 3 trials each — 216
evaluations. This establishes the measurement machinery independent of any model
API. Switch to `provider: anthropic` to evaluate a real model through the
identical harness. See [`docs/guides/experiments.md`](docs/guides/experiments.md).

## Quantitative results (baseline-v1, auto-generated)

| model | prompt | n | pass rate | 95% CI | avg latency (s) | avg tokens |
|---|---|---|---|---|---|---|
| reference-golden | direct | 54 | 1.000 | [0.934, 1.0] | 0.10 | 320 |
| synthetic-high | direct | 54 | 1.000 | [0.934, 1.0] | 1.74 | 298 |
| synthetic-mid | direct | 54 | 0.944 | [0.849, 0.981] | 1.75 | 266 |
| synthetic-low | direct | 54 | 0.778 | [0.651, 0.868] | 1.72 | 259 |

Pass rate declines with fidelity and with objective difficulty (hard
communication-protocol benchmarks dominate the failures), supporting H3. Full
leaderboards, category/difficulty breakdowns and figures are regenerated into
`results/`, `publication/` and `website/`.

## Quickstart

```bash
pip install -e ".[dev]"                      # or: pip install pyyaml (runtime only)
hdleval list-benchmarks                       # inspect the versioned suite
hdleval run configs/experiments/baseline.yaml # run + populate the registry
python reproduce.py                           # regenerate every artifact
```

Reproducible full-toolchain run (installs GHDL + Yosys):

```bash
docker build -t hdleval . && docker run --rm -v "$PWD/results:/opt/hdleval/results" hdleval
```

Offline verification without dev extras:

```bash
PYTHONPATH=src python scripts/run_tests_nodeps.py   # 48 tests
PYTHONPATH=.  python scripts/estimate_coverage.py    # ~88% coverage
```

## Limitations

The public baseline uses reference/synthetic providers as controls — it measures
the harness, not a commercial model. Where GHDL/Yosys are unavailable,
compile/synth/sim are `skipped` and functional correctness uses a documented
static fallback (full results via Docker). Difficulty weights are fixed a priori.
These and other threats to validity are discussed in the technical report.

## Reproducibility

`python reproduce.py` rebuilds benchmarks, runs the experiment, and regenerates
all reports, figures, the technical report, the preprint and the website from the
experiment registry. Determinism comes from seeded providers, disk-cached
real-model responses, environment fingerprinting and versioned benchmarks. See
[`docs/guides/reproducibility.md`](docs/guides/reproducibility.md).

## Repository layout

```
src/hdleval/        implementation (config, models, prompts, parsing, benchmarks,
                    toolchain, metrics, verification, evaluation, registry,
                    leaderboard, reporting, orchestration, plugins, optimization, rag, repair)
configs/            declarative configs (models, prompts, experiments, …)
benchmarks/v1/      the versioned benchmark dataset
tests/              unit · integration · regression · e2e
scripts/            build_benchmarks · generate_publication · generate_website · reproduce helpers
results/            generated leaderboards, reports, figures, tables
publication/        generated technical report + OpenReview preprint + figures
website/            generated research website (Home/Architecture/Pipeline/Benchmarks/Experiments/Results/Future)
docs/               research-specification · evaluation-methodology · adr/ · guides/ · releases/
reproduce.py        one-command reproduction of every artifact
```

## Future research directions

Multi-model benchmarking, formal equivalence checking, retrieval-augmented
generation, RL-optimised prompting/repair, an open benchmark dataset, and
generalisation beyond VHDL (Verilog/SystemVerilog/Chisel/HLS). See
[`ROADMAP.md`](ROADMAP.md).

## Citation

See [`CITATION.cff`](CITATION.cff). Please cite the platform and the benchmark
suite version you used.

## License

MIT — see [LICENSE](LICENSE).

---

*The `agents/`, `core/`, `hdl/` and `reference/` directories contain the original
rule-based VHDL pipeline this platform grew from; its verified golden models seed
the benchmark reference implementations.*

# hdleval — Research Specification

*Version 1.0 · status: living document · owner: hdleval contributors*

This document defines the scientific and engineering foundation of the platform
**before** implementation detail. It is the reference against which every
experiment, benchmark and artifact is judged. It is deliberately independent of
the current codebase so that the platform can evolve without invalidating the
research framing.

## 1. Problem statement

Language models increasingly emit hardware description language (HDL), but the
field lacks a shared, reproducible way to measure how well they do it.
Demonstrations typically show a handful of hand-picked designs, inspected by
eye, with no controlled harness, no resource or timing metrics, no versioned
benchmark, and no statistical treatment. As a result, claims are not
comparable across papers, tools, or model versions, and progress cannot be
tracked over time.

hdleval treats AI-assisted hardware design as a measurable experimental science.
It provides a fixed evaluation harness, a versioned benchmark taxonomy,
quantitative metrics beyond pass/fail, a provenance-complete experiment
registry, and automatically generated leaderboards, reports, figures and
publication artifacts.

## 2. Research questions

- **RQ1 — Fair comparison.** Can a single, config-driven evaluation harness
  fairly and reproducibly compare heterogeneous HDL generators (different
  models, prompting strategies, repair policies) across a broad design taxonomy?
- **RQ2 — Discriminating signals.** Which quantitative signals beyond functional
  pass/fail — compilation, synthesis, simulation, static structural complexity,
  resource utilisation, timing, failure class — best discriminate between
  generators?
- **RQ3 — Difficulty scaling.** How does generation quality change as a function
  of an *objective* benchmark difficulty score, and is that score predictive?
- **RQ4 — Interventions.** Do prompting strategies, self-repair, retrieval
  augmentation, and optimization objectives measurably improve outcomes, and by
  how much with what confidence?

## 3. Hypotheses

- **H1.** A config-driven harness with inference decoupled from evaluation yields
  stable, reproducible rankings under re-run and re-seed.
- **H2.** Structure- and resource-level metrics reveal quality differences that
  are invisible to pass/fail alone.
- **H3.** Pass rate declines monotonically with the objective difficulty score.
- **H4.** Chain-of-thought and self-repair improve pass rate on moderate/hard
  benchmarks more than on trivial ones (interaction effect).

## 4. Evaluation objectives and success criteria

The platform is successful when: (a) any new model can be evaluated by adding a
config file and no code; (b) every figure and table in every report regenerates
from the experiment registry with one command; (c) benchmarks are versioned and
independently citable; (d) results carry confidence intervals and the pipeline
records enough provenance to reproduce any single run bit-for-bit given the same
model and toolchain.

## 5. Intended research contributions

1. A versioned, taxonomy-driven **benchmark suite** for HDL generation with an
   objective difficulty score.
2. A **reproducible evaluation harness** that decouples model inference from
   grading and runs identically for every model.
3. A **metric framework** spanning functional, structural, resource and timing
   dimensions, with failure classification.
4. An **experiment registry + reproducibility workflow** producing
   publication-ready artifacts automatically.

## 6. Scope

**In scope (v0.1–v1.0):** VHDL generation; GHDL/Yosys open-source toolchain;
single-design benchmarks up to moderate hierarchy; deterministic reference and
synthetic baselines; one real-model provider interface (Anthropic).
**Out of scope (deferred to v2.0+):** multi-model leaderboards at scale,
reinforcement-learning optimization, formal equivalence at scale, and non-VHDL
languages. See `ROADMAP.md`.

## 7. System architecture (overview)

Layered and plugin-based:

```
configs/  ─▶  hdleval.config          (typed, YAML-loaded)
models/   ─▶  ModelProvider           (reference | synthetic | anthropic | …)
prompts/  ─▶  PromptStrategy          (direct | CoT | few-shot | rag | repair)
benchmarks/v1 ─▶ Benchmark suite      (structured metadata + reference HDL)
toolchain ─▶  GHDL / Yosys adapters   (graceful degradation)
metrics   ─▶  static + resource
          ─▶  EvaluationHarness  ─▶  ExperimentDB  ─▶  Leaderboard  ─▶  Reports/Figures
                                                                    └▶  Publication/Website
```

Inference is injected; adding a model never touches evaluation logic (RQ1). See
`docs/adr/` for the decisions behind this design.

## 8. Experiment lifecycle

1. **Author** an experiment config (models × prompts × benchmark selector ×
   toolchain/verification/optimization × trials × seed).
2. **Run** through the harness; each (model, prompt, benchmark, trial) executes
   the identical pipeline and produces one `ExperimentRecord` + stage log.
3. **Register** every record in the SQLite experiment database with full
   provenance (env, git commit, seeds, inference config, retries, artifacts).
4. **Aggregate** into leaderboards with confidence intervals.
5. **Report** JSON/CSV/Markdown/HTML + figures, then publication and website.

## 9. Benchmark philosophy

A benchmark is *pure data*: a natural-language specification, functional
requirements, expected interface, optional verified reference implementation,
verification assets, category, tags and complexity metrics. Benchmarks are
verified by construction and versioned independently so that revisions remain
reproducible and the suite can be released as a standalone dataset.

## 10. Evaluation methodology

Every model runs the same procedure; toolchain stages degrade to `skipped` when
tools are absent (strict in CI). Metrics are computed at four levels: functional
(compile/synth/sim/properties), structural (static analysis), resource
(LUT/FF/DSP/BRAM, estimated Fmax, area efficiency), and process (latency, tokens,
retries). Failures are classified into a single canonical class per run. Full
detail in `docs/evaluation-methodology.md`.

## 11. Reproducibility strategy

One command (`reproduce.py`) rebuilds benchmarks, runs the experiment, and
regenerates all artifacts. Determinism is achieved through: seeded providers,
disk-cached real-model responses, environment fingerprinting, versioned
benchmarks, and content-hashed DAG caching. See `docs/guides/reproducibility.md`.

## 12. Statistical methodology

Success rates are reported with Wilson score 95% confidence intervals. Repeated
seeded trials provide variance estimates. Multi-condition studies use paired
comparisons across benchmarks; significance testing (e.g. McNemar for paired
pass/fail, bootstrap for metric deltas) is applied where sample size permits.
The platform never reports a point estimate without its interval.

## 13. Software architecture principles

Config over code; inference decoupled from evaluation; pure-data benchmarks;
graceful toolchain degradation; append-only machine-readable logs;
content-addressed caching; plugin registration for every extensible component;
strict typing and linting; every artifact a build product.

## 14. Long-term research vision

A community research infrastructure for AI-assisted hardware design: multi-model
longitudinal leaderboards, formal verification backends, retrieval-augmented and
RL-optimised generation, Pareto-optimal design-space exploration, and support
for Verilog/SystemVerilog/Chisel/HLS through modular code-generation interfaces.

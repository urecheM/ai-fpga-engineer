# Roadmap

hdleval evolves from a prototype into long-term research infrastructure. Each
milestone is a versioned, releasable increment with its own artifacts.

## v0.1 — Prototype (HDL generation) · **current**
- Config-driven core; `ModelProvider` interface (reference, synthetic, anthropic)
- Versioned benchmark suite (v1) across 7 categories with objective difficulty
- Evaluation harness (load→prompt→infer→parse→compile→synth→sim→metrics→classify)
- Experiment registry (SQLite) with full provenance; structured JSONL logging
- Leaderboards with Wilson confidence intervals; auto reports/figures/website
- Engineering foundation: pytest+coverage, Ruff, mypy, pre-commit, Docker,
  dev container, CI, issue templates
- `reproduce.py` regenerates every artifact

## v0.5 — Verification
- GHDL simulation with per-benchmark self-checking testbenches (reference vectors)
- Formal property checking backend (SymbiYosys) behind the property interface
- Equivalence checking of generated HDL vs reference where feasible
- Mutation-campaign evidence that verification has discriminating power
- Expanded failure taxonomy with timing-closure analysis

## v1.0 — Benchmarking
- Enlarged, calibrated benchmark suite (v2) with empirically fitted difficulty
- Repeated-trial statistics, significance testing, variance analysis as defaults
- Category- and difficulty-tier leaderboards; longitudinal trends across releases
- Pareto frontiers for area-vs-performance; resource-utilisation histograms
- Public technical report + OpenReview preprint generated from results

## v2.0 — Multi-model benchmarking
- Multiple real model providers through the common interface
- Cost/latency/token accounting and throughput leaderboards
- Cross-release historical comparison dashboards
- Hugging Face dataset + Papers With Code registration

## v3.0 — Reinforcement-learning optimization
- RL/optimisation of prompting, retry policies, and repair strategies
- Retrieval-augmented generation over vendor/protocol documentation
- Constraint-aware, multi-objective (area/power/timing/latency/throughput) generation
- Automated failure-diagnosis and self-repair agents with repair statistics

## v4.0 — Open benchmark dataset
- Community benchmark contributions via issue templates + validation pipeline
- Multi-language generation: Verilog, SystemVerilog, Chisel, SpinalHDL, HLS
- DAG-based orchestration at scale with caching and parallel scheduling
- Stable public leaderboard and dataset governance

# Evaluation methodology

## The identical procedure
Every (model, prompt, benchmark, trial) runs:
`load spec → build prompt → infer → parse → compile → synthesize → simulate →
compute metrics → check properties → classify failure → record`.

## Metric levels
- **Functional:** compilation, synthesis, simulation success; property results;
  functional correctness (a passing simulation against reference vectors, or the
  documented static fallback when no simulator is present).
- **Structural (tool-free, deterministic):** hierarchy depth, combinational
  complexity, inferred-latch risk, reset strategy, FSM state count, module
  decomposition, fan-out, modularity.
- **Resource:** LUTs, flip-flops, DSP, BRAM; estimated maximum clock frequency;
  area efficiency (from Yosys `stat`).
- **Process:** inference latency, token usage, retry count, wall-clock duration.

## Difficulty scoring
An objective weighted sum over state complexity, arithmetic complexity,
concurrency, hierarchy depth, timing constraints, interface count and control
complexity, normalised to 0–100 and bucketed into trivial/easy/moderate/hard/
expert. Weights are fixed per suite version (`benchmarks/difficulty.py`).

## Failure classification
A single canonical class per run, by first failing stage: `no_code_generated`,
`syntax_error`, `compilation_error`, `synthesis_failure`, `simulation_failure`,
`protocol_violation`, `timing_failure`, `verification_failure`,
`optimization_failure`.

## Statistics
Pass rates carry Wilson score 95% confidence intervals. Seeded repeated trials
give variance; paired per-benchmark comparisons support significance testing
(McNemar for paired pass/fail; bootstrap for metric deltas).

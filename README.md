---
license: mit
language:
  - en
task_categories:
  - text-generation
tags:
  - hardware
  - vhdl
  - fpga
  - eda
  - benchmark
  - llm-evaluation
  - code-generation
pretty_name: LLM FPGA Benchmark
size_categories:
  - n<1K
configs:
  - config_name: default
    data_files:
      - split: train
        path: data/benchmarks.jsonl
---

# llm-fpga-benchmark

Benchmark dataset for evaluating LLM-generated VHDL designs, intended for
synthesis and verification benchmarking. Exported from the
[hdleval](https://github.com/urecheM/ai-fpga-engineer/tree/main/src/hdleval) research platform, benchmark
suite **v1**.

## Dataset Description

18 hardware design tasks, each a self-contained record pairing a
natural-language specification (the prompt) with a **verified VHDL-2008
reference implementation**, category, and an objective difficulty tier.

Core fields:

```json
{
  "prompt":          "Design a synchronous FIFO, 8-bit wide, depth 16, ...",
  "vhdl_reference":  "library ieee; ...",
  "category":        "memory",
  "difficulty":      "moderate"
}
```

Additional fields: `id`, `title`, `entity` (expected top-level entity name),
`functional_requirements`, `properties` (verification properties, e.g.
`overflow_detection`), `tags`, `difficulty_score` (0–100), `suite_version`.

The repository also ships `data/baseline_results.csv`: 216 per-record,
toolchain-backed (GHDL + Yosys) evaluation outcomes of four controlled
generators over this suite (fields: model, benchmark, category, difficulty,
trial, passed, compiled, synthesized, simulated, failure_class, latency,
tokens, LUT/FF counts, estimated Fmax).

## Motivation

Evaluation of LLM-generated HDL is largely anecdotal: hand-picked designs, no
shared versioned benchmark, no resource metrics, no statistics. Unlike
software, HDL correctness requires compiling under strict language semantics,
synthesizing to a realisable netlist, and simulating against reference
stimuli. This dataset provides a versioned, citable suite so that claims
become comparable across models, prompts and papers — with VHDL coverage,
which existing Verilog-centric suites (VerilogEval, RTLLM) do not provide.

## Collection Process

Benchmarks are authored as **pure data** (YAML metadata + reference HDL) in
the hdleval repository, verified by construction: every reference
implementation compiles, synthesizes and simulates correctly under the
platform's GHDL/Yosys harness, and the suite is exercised by the platform's
CI, negative tests and mutation campaigns. The difficulty tier derives from a
fixed weighted sum over seven declared complexity dimensions (state,
arithmetic, concurrency, hierarchy, timing, interface, control), normalised to
0–100; weights are fixed per suite version and not fitted to any model.
Baseline results come from experiment `baseline-v1`: 4 providers × 18 tasks ×
3 seeded trials with full provenance (git commit, seeds, environment) recorded
in the platform registry.

## Categories

| category | tasks | examples |
|---|---|---|
| arithmetic | 4 | ripple-carry adder, ALU, comparator, multiplier |
| communication | 3 | UART TX, SPI master, I2C controller |
| memory | 3 | synchronous FIFO, register file, RAM |
| fsm | 2 | sequence detector, traffic-light controller |
| dsp | 2 | 4-tap FIR, moving-average filter |
| processor | 2 | ALU control decoder, branch predictor |
| control | 2 | debouncer, PWM generator |

Difficulty tiers: 1 trivial, 8 easy, 6 moderate, 3 hard.

## Limitations

- 18 single-design tasks of at most moderate hierarchy; no large hierarchical
  or multi-clock designs, and no expert-tier tasks in v1.
- VHDL-2008 only; Verilog/SystemVerilog/Chisel variants are future work.
- Difficulty weights are a priori engineering judgements, not yet empirically
  calibrated against model outcomes.
- Reference implementations are verified by construction and mutation testing,
  but not exhaustively for wide operands.
- The shipped baseline results evaluate controlled providers (reference replay
  and synthetic fault injection), which validate the measurement harness; they
  are not claims about any commercial LLM.
- In `baseline_results.csv`, the `luts`/`ffs` columns are present but zero
  (Yosys stat counters were not populated in the `baseline-v1` export);
  `est_fmax_mhz` and `hdl_lines` are populated.

## Citation

```bibtex
@misc{llmfpgabenchmark2026,
  title  = {llm-fpga-benchmark: A Benchmark Dataset for Evaluating
            LLM-Generated VHDL Designs},
  author = {Ureche, Clara and the hdleval contributors},
  year   = {2026},
  note   = {Benchmark suite v1, hdleval platform v0.1},
  url    = {https://github.com/urecheM/ai-fpga-engineer/tree/main/src/hdleval}
}
```

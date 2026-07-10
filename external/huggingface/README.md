---
license: mit
task_categories:
  - text-generation
tags:
  - hardware-design
  - vhdl
  - hdl
  - benchmark
  - eda
pretty_name: hdleval Benchmark Suite (v1)
size_categories:
  - n<1K
configs:
  - config_name: default
    data_files: data/benchmarks.jsonl
---

# hdleval Benchmark Suite (v1)

A versioned benchmark suite for evaluating LLM-assisted hardware design in
VHDL, produced by the [hdleval](https://github.com/your-org/hdleval) research
platform.

## Description

18 benchmarks across seven categories — arithmetic, finite-state machines,
communication protocols, memory, processors, DSP and control — each with a
natural-language specification, functional requirements, expected interface, a
verified reference implementation, complexity metrics and an objective
difficulty score.

## Taxonomy

`arithmetic` · `fsm` · `communication` · `memory` · `processor` · `dsp` · `control`

## Fields

`id`, `version`, `category`, `title`, `specification`, `functional_requirements`,
`expected_behavior`, `entity`, `interfaces`, `tags`, `complexity`,
`estimated_difficulty`, `properties`, `reference_hdl`.

## Difficulty

Objective weighted score (0–100) over state, arithmetic, concurrency, hierarchy,
timing, interface and control complexity; bucketed trivial→expert. Fixed per
suite version.

## Versioning

The suite is versioned independently of the platform (`v1` → semantic `1.x`).
Future revisions are additive and preserve reproducibility of prior results.

## Usage

```python
from datasets import load_dataset
ds = load_dataset("your-org/hdleval-benchmarks", split="train")
print(ds[0]["specification"])
```

## Limitations

Reference implementations are verified by construction and simulation but not
exhaustively; specifications are English-only in v1; the suite targets VHDL-2008.

## Citation

See `CITATION.cff` in the hdleval repository. License: MIT.

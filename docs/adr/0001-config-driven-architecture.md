# ADR 0001 — Config-driven architecture

## Status
Accepted

## Context
Early hardware-generation experiments hard-code the model, prompt and benchmark
into scripts. Comparing conditions then means editing code, which is error-prone
and irreproducible.

## Decision
Every runtime object — models, prompts, benchmarks, synthesis, verification,
optimization, experiments — is a typed dataclass loaded from YAML under
`configs/`. Experiments compose these by name. No execution logic is hard-coded.

## Consequences
+ New models/prompts/benchmarks require config only, not code (RQ1).
+ Experiments are declarative and diffable.
− A config schema must be maintained and validated (`config/schema.py`).

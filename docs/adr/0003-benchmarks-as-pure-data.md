# ADR 0003 — Benchmarks as versioned pure data

## Status
Accepted

## Context
Benchmarks embedded in code cannot be versioned, cited, or released
independently, and mix specification with grading logic.

## Decision
A benchmark is structured metadata (YAML) + optional reference HDL + verification
assets, under `benchmarks/<suite-version>/<id>/`. Difficulty is an objective
weighted score. The suite is versioned separately from the platform.

## Consequences
+ The suite can be released as a standalone dataset (Hugging Face) and cited.
+ Revisions remain reproducible via suite versioning.
− Reference implementations must be verified and maintained.

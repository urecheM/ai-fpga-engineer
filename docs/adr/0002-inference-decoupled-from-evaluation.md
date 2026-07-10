# ADR 0002 — Decouple model inference from evaluation

## Status
Accepted

## Context
If evaluation logic knows about specific model APIs, adding a model means
changing the harness, biasing comparisons and coupling concerns.

## Decision
Inference is a `ModelProvider` that turns a `ModelRequest` into a
`ModelResponse`. The harness depends only on this interface. Providers
(reference, synthetic, anthropic, …) are registered in a registry.

## Consequences
+ Identical evaluation for every model; new models drop in behind the interface.
+ Deterministic providers make the whole pipeline reproducible without a key.
− Provider-specific features (tools, streaming) must be normalised to the interface.

# ADR 0004 — Graceful toolchain degradation

## Status
Accepted

## Context
GHDL/Yosys are not always installed (laptops, CI matrices, reviewers). Requiring
them everywhere blocks the pipeline; ignoring their absence hides it.

## Decision
Toolchain adapters return `status='skipped'` (not `fail`) when a tool is absent.
The harness records this explicitly, and functional correctness falls back to a
weaker, clearly-labelled static signal. CI sets `HDLEVAL_REQUIRE_TOOLS=1` and the
Docker image installs the tools for full runs.

## Consequences
+ The platform runs anywhere; results always carry the toolchain fingerprint.
− "skipped" results must be interpreted carefully; documented as a threat to validity.

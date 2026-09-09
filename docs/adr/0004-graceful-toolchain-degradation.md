# ADR 0004 — Graceful toolchain degradation

## Status
Accepted

## Context
GHDL/Yosys are not always installed (laptops, CI matrices, reviewers). Requiring
them everywhere blocks the pipeline; ignoring their absence hides it.

## Decision
Toolchain adapters return `status='skipped'` (not `fail`) when a tool is absent.
The harness records this explicitly, and functional correctness falls back to a
weaker, clearly-labelled static signal. GitHub Actions CI installs GHDL + Yosys
directly (see `.github/workflows/ci.yml`) so these stages run for real instead of
degrading; the Docker image does the same for local full runs.
`toolchain.detect.require_tools()` (gated on `HDLEVAL_REQUIRE_TOOLS=1`) exists as
an opt-in hard-fail switch but is not yet wired into the harness — see the
"known limitations" note in `docs/CLAIMS.md`.

## Consequences
+ The platform runs anywhere; results always carry the toolchain fingerprint.
− "skipped" results must be interpreted carefully; documented as a threat to validity.

# Benchmark documentation

## Taxonomy
arithmetic · finite-state machines · communication protocols · memory ·
processors · digital signal processing · control.

## Structure
`benchmarks/v1/<id>/benchmark.yaml` + `reference.vhd` (+ optional testbench).
Metadata: id, version, category, title, specification, functional_requirements,
expected_behavior, entity, interfaces, tags, complexity, reference_hdl_path,
properties, estimated_difficulty.

## Difficulty
Objective weighted score (see `evaluation-methodology.md`) → tier.

## Validation
Reference implementations are verified by construction; the build script
materialises the suite. Full simulation-based validation runs in the Docker
image (GHDL). New benchmarks enter via the benchmark-submission issue template.

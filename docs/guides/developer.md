# Developer guide

## Setup
```bash
make install          # editable install + pre-commit hooks
make test             # pytest
make cov              # coverage (term + html)
make lint             # ruff check + format --check
make type             # mypy
make reproduce        # full artifact regeneration
```
Without the dev extras you can still verify logic offline:
```bash
PYTHONPATH=src python scripts/run_tests_nodeps.py
PYTHONPATH=. python scripts/estimate_coverage.py
```

## Layout
`src/hdleval` implementation · `configs/` declarative configs ·
`benchmarks/v1` dataset · `tests/{unit,integration,regression,e2e}` ·
`scripts/` build/generate tools · `results/` generated · `publication/`,
`website/` generated · `docs/` including `adr/` and `guides/`.

## Conventions
Config over code; deterministic pure functions; serialisable dataclasses;
type hints everywhere; every artifact a build product. Pre-commit runs Ruff,
mypy and the test suite before any commit.

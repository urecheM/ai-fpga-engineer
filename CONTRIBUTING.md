# Contributing to hdleval

Thanks for your interest! hdleval is research infrastructure; contributions of
benchmarks, model providers, metrics and experiments are especially welcome.

## Workflow
1. Open an issue (bug, feature, benchmark submission, or research proposal) using
   the templates.
2. `make install` to set up the environment and pre-commit hooks.
3. Make your change with tests. Pre-commit runs Ruff, mypy and pytest.
4. Ensure `make lint type test` pass and coverage does not regress.
5. Open a PR describing the research or engineering rationale.

## Adding benchmarks / providers / metrics
See `docs/guides/extension-guide.md`.

## Code of conduct
Be respectful and constructive. Assume good faith.

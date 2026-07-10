#!/usr/bin/env bash
# Local quality gate: run the same checks CI runs, in order.
# Usage:  ./scripts/check.sh          (report only)
#         ./scripts/check.sh --fix    (auto-fix ruff issues first)
# Supports Task 2 (flip Ruff/mypy CI back to strict) in
# docs/guides/implementation-tasks.md.
set -uo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--fix" ]]; then
  echo "== ruff --fix =="; ruff check --fix src tests scripts
  echo "== ruff format =="; ruff format src tests scripts
fi

rc=0
echo "== ruff check ==";        ruff check src tests scripts        || rc=1
echo "== ruff format --check =="; ruff format --check src tests scripts || rc=1
echo "== mypy ==";             mypy src/hdleval                    || rc=1
echo "== pytest ==";           pytest -q                           || rc=1

if [[ $rc -eq 0 ]]; then
  echo -e "\nAll checks passed — safe to flip CI to strict."
else
  echo -e "\nSome checks failed — fix before making CI strict."
fi
exit $rc

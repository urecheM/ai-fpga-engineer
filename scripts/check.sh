#!/usr/bin/env bash
# Local 
#run same checks as ci
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
  echo -e "\nAll checks passed. Safe to flip CI to strict."
else
  echo -e "\nSome checks failed. Fix before making CI strict."
fi
exit $rc

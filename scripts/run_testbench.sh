#!/usr/bin/env bash
# Analyze + elaborate + run a benchmark's reference design against its testbench.
# Usage:  ./scripts/run_testbench.sh <benchmark_id> <tb_entity>
#   e.g.  ./scripts/run_testbench.sh comm_uart_tx uart_tx_tb
# A pass prints "ALL TESTS PASSED"; a mismatch ends with severity failure.
# Supports Task 3 in docs/guides/implementation-tasks.md.
set -euo pipefail
cd "$(dirname "$0")/.."

id="${1:?usage: run_testbench.sh <benchmark_id> <tb_entity>}"
tb="${2:?usage: run_testbench.sh <benchmark_id> <tb_entity>}"
dir="benchmarks/v1/$id"

command -v ghdl >/dev/null || { echo "ghdl not on PATH (install OSS CAD Suite)"; exit 2; }
[[ -f "$dir/reference.vhd" ]] || { echo "no reference.vhd in $dir"; exit 2; }
[[ -f "$dir/testbench.vhd" ]] || { echo "no testbench.vhd in $dir"; exit 2; }

work="$(mktemp -d)"
cp "$dir/reference.vhd" "$dir/testbench.vhd" "$work/"
( cd "$work"
  ghdl -a --std=08 reference.vhd testbench.vhd
  ghdl -e --std=08 "$tb"
  ghdl -r --std=08 "$tb" --assert-level=error )

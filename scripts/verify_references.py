"""Analyze every v1 reference design under GHDL and report pass/fail.

Usage:  python scripts/verify_references.py
Exit code 0 = all analyze cleanly, 1 = one or more failed, 2 = ghdl not found.
Requires GHDL on PATH (install the OSS CAD Suite). This is the check behind
Task 1 in docs/guides/implementation-tasks.md.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "benchmarks" / "v1"


def main() -> int:
    if not shutil.which("ghdl"):
        print("ghdl not found on PATH. Install the OSS CAD Suite and re-run.")
        return 2
    refs = sorted(V1.glob("*/reference.vhd"))
    if not refs:
        print(f"no reference designs found under {V1}")
        return 2
    failures: list[tuple[str, str]] = []
    for ref in refs:
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run(
                ["ghdl", "-a", "--std=08", str(ref)],
                capture_output=True,
                text=True,
                cwd=d,
            )
        ok = r.returncode == 0
        print(f"{'ok ' if ok else 'FAIL':4}  {ref.parent.name}")
        if not ok:
            failures.append((ref.parent.name, r.stderr.strip()))
    print(f"\n{len(refs) - len(failures)} ok, {len(failures)} failed")
    for name, err in failures:
        print(f"\n--- {name} ---\n{err}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

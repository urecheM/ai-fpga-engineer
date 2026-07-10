"""Every v1 reference design must analyze under GHDL (skipped if ghdl absent)."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from hdleval.benchmarks.loader import load_suite, reference_hdl

_SUITE = load_suite("v1")


@pytest.mark.skipif(shutil.which("ghdl") is None, reason="ghdl not installed")
@pytest.mark.parametrize("bench", _SUITE, ids=[b.id for b in _SUITE])
def test_reference_compiles(bench):
    code = reference_hdl(bench)
    assert code.strip(), f"{bench.id} has no reference HDL"
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "ref.vhd"
        p.write_text(code)
        r = subprocess.run(
            ["ghdl", "-a", "--std=08", str(p)],
            capture_output=True, text=True, cwd=d,
        )
    assert r.returncode == 0, f"{bench.id} failed GHDL analysis:\n{r.stderr}"

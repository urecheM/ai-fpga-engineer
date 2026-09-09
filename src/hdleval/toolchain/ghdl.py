"""GHDL adapter: analyze/elaborate for compilation, run a testbench for sim."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from .detect import ToolResult, detect


def compile_vhdl(vhdl: str, *, entity: str | None = None, timeout: float = 60.0) -> ToolResult:
    """Analyze + elaborate a VHDL design. status='skipped' if GHDL absent."""
    tc = detect()
    if not tc.has("ghdl"):
        return ToolResult(status="skipped", stderr="ghdl not installed")
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "design.vhd"
        src.write_text(vhdl)
        try:
            a = subprocess.run(
                ["ghdl", "-a", "--std=08", str(src)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=d,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(status="fail", stderr="ghdl analyze timeout")
        if a.returncode != 0:
            return ToolResult(
                status="fail", stdout=a.stdout, stderr=a.stderr, returncode=a.returncode
            )
        if entity:
            e = subprocess.run(
                ["ghdl", "-e", "--std=08", entity],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=d,
            )
            if e.returncode != 0:
                return ToolResult(
                    status="fail", stdout=e.stdout, stderr=e.stderr, returncode=e.returncode
                )
        return ToolResult(status="ok", stdout=a.stdout)


def simulate(
    design_vhdl: str, testbench_vhdl: str, tb_entity: str, *, timeout: float = 120.0
) -> ToolResult:
    """Run design + testbench under GHDL. A GHDL assertion failure => sim fail."""
    tc = detect()
    if not tc.has("ghdl"):
        return ToolResult(status="skipped", stderr="ghdl not installed")
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "design.vhd").write_text(design_vhdl)
        (Path(d) / "tb.vhd").write_text(testbench_vhdl)
        try:
            subprocess.run(
                ["ghdl", "-a", "--std=08", "design.vhd", "tb.vhd"],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=d,
                check=True,
            )
            subprocess.run(
                ["ghdl", "-e", "--std=08", tb_entity],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=d,
                check=True,
            )
            r = subprocess.run(
                ["ghdl", "-r", "--std=08", tb_entity, "--assert-level=error"],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=d,
            )
        except subprocess.CalledProcessError as exc:
            return ToolResult(status="fail", stdout=exc.stdout or "", stderr=exc.stderr or "")
        except subprocess.TimeoutExpired:
            return ToolResult(status="fail", stderr="ghdl sim timeout")
        status = "ok" if r.returncode == 0 and "error" not in r.stderr.lower() else "fail"
        return ToolResult(status=status, stdout=r.stdout, stderr=r.stderr, returncode=r.returncode)

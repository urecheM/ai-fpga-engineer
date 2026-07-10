"""Yosys adapter: synthesize VHDL (via ghdl plugin) and parse resource stats."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from .detect import ToolResult, detect


def synthesize(vhdl: str, entity: str, *, target: str = "ice40", timeout: float = 180.0) -> ToolResult:
    """Run Yosys synthesis, returning resource utilisation metrics.

    Requires the ghdl-yosys-plugin. status='skipped' when unavailable.
    """
    tc = detect()
    if not (tc.has("yosys") and tc.ghdl_plugin):
        return ToolResult(status="skipped", stderr="yosys/ghdl-plugin not available")
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "design.vhd").write_text(vhdl)
        stat = Path(d) / "stat.json"
        synth_cmd = "synth_ice40" if target == "ice40" else "synth"
        script = (
            f"plugin -i ghdl; ghdl --std=08 design.vhd -e {entity}; "
            f"{synth_cmd}; tee -o {stat} stat -json"
        )
        try:
            r = subprocess.run(["yosys", "-p", script],
                               capture_output=True, text=True, timeout=timeout, cwd=d)
        except subprocess.TimeoutExpired:
            return ToolResult(status="fail", stderr="yosys timeout")
        if r.returncode != 0:
            return ToolResult(status="fail", stdout=r.stdout, stderr=r.stderr,
                              returncode=r.returncode)
        metrics: dict[str, float] = {}
        if stat.exists():
            try:
                data = json.loads(stat.read_text())
                cells = data.get("modules", {}).get(entity, {}).get("num_cells_by_type", {})
                metrics["luts"] = float(sum(v for k, v in cells.items() if "LUT" in k.upper()))
                metrics["ffs"] = float(sum(v for k, v in cells.items()
                                           if "DFF" in k.upper() or "FF" in k.upper()))
                metrics["dsp"] = float(sum(v for k, v in cells.items() if "MAC" in k.upper()
                                           or "DSP" in k.upper()))
                metrics["bram"] = float(sum(v for k, v in cells.items() if "RAM" in k.upper()))
            except Exception:
                pass
        return ToolResult(status="ok", stdout=r.stdout, metrics=metrics)

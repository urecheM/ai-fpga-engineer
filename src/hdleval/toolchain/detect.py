"""Detect which HDL tools are present in the environment."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field

TOOLS = ("ghdl", "yosys", "nextpnr-ice40")


@dataclass(frozen=True)
class ToolResult:
    """Uniform result of a toolchain stage."""

    status: str  # ok | fail | skipped
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "ok"


@dataclass
class Toolchain:
    present: dict[str, bool] = field(default_factory=dict)
    ghdl_plugin: bool = False

    def has(self, tool: str) -> bool:
        return self.present.get(tool, False)

    def summary(self) -> str:
        bits = [f"{t}={'yes' if self.present.get(t) else 'no'}" for t in TOOLS]
        bits.append(f"ghdl-yosys-plugin={'yes' if self.ghdl_plugin else 'no'}")
        return ", ".join(bits)


def require_tools() -> bool:
    return os.environ.get("HDLEVAL_REQUIRE_TOOLS", "") == "1"

class ToolchainMissingError(RuntimeError):
    """Raised when HDLEVAL_REQUIRE_TOOLS=1 and a required tool is absent."""


def missing_tools(
    tc: Toolchain, *, place_and_route: bool = False, equivalence: bool = False
) -> list[str]:
    """Tools the evaluation needs that this environment lacks."""
    missing = [t for t in ("ghdl", "yosys") if not tc.has(t)]
    if tc.has("yosys") and not tc.ghdl_plugin:
        missing.append("ghdl-yosys-plugin")
    if place_and_route and not tc.has("nextpnr-ice40"):
        missing.append("nextpnr-ice40")
    if equivalence and not shutil.which("sby"):
        missing.append("sby (SymbiYosys)")
    return missing

def _ghdl_plugin_ok(timeout: float = 30.0) -> bool:
    if not shutil.which("yosys"):
        return False
    try:
        r = subprocess.run(
            ["yosys", "-p", "plugin -i ghdl"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return r.returncode == 0
    except Exception:
        return False


_CACHE: Toolchain | None = None


def detect(refresh: bool = False) -> Toolchain:
    global _CACHE
    if _CACHE is None or refresh:
        tc = Toolchain({t: shutil.which(t) is not None for t in TOOLS})
        tc.ghdl_plugin = _ghdl_plugin_ok() if tc.present.get("yosys") else False
        _CACHE = tc
    return _CACHE

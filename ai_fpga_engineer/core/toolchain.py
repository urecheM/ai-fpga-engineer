"""EDA toolchain discovery and the require-tools policy."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field

TOOLS = ("ghdl", "yosys", "nextpnr-ice40", "sby", "icepack")


def have(tool: str) -> bool:
    return shutil.which(tool) is not None


def require_tools() -> bool:
    """True when the environment demands real tools (CI sets this)."""
    return os.environ.get("AIFPGA_REQUIRE_TOOLS", "") == "1"


def ghdl_plugin_ok(timeout: float = 30.0) -> bool:
    """True if yosys can load the GHDL front-end plugin (needed for VHDL synth)."""
    if not have("yosys"):
        return False
    try:
        r = subprocess.run(["yosys", "-p", "plugin -i ghdl"],
                           capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0
    except Exception:
        return False


@dataclass
class Toolchain:
    present: dict[str, bool] = field(default_factory=dict)
    ghdl_plugin: bool = False

    @property
    def sim_ok(self) -> bool:
        return self.present.get("ghdl", False)

    @property
    def pnr_ok(self) -> bool:
        return (self.present.get("yosys", False) and self.ghdl_plugin
                and self.present.get("nextpnr-ice40", False))

    @property
    def formal_ok(self) -> bool:
        return self.present.get("sby", False) and self.ghdl_plugin

    def missing(self) -> list[str]:
        return [t for t in TOOLS if not self.present.get(t, False)]

    def summary(self) -> str:
        bits = [f"{t}={'yes' if self.present.get(t) else 'NO'}" for t in TOOLS]
        bits.append(f"ghdl-yosys-plugin={'yes' if self.ghdl_plugin else 'NO'}")
        return ", ".join(bits)


_CACHE: Toolchain | None = None


def detect(refresh: bool = False) -> Toolchain:
    global _CACHE
    if _CACHE is None or refresh:
        tc = Toolchain({t: have(t) for t in TOOLS})
        tc.ghdl_plugin = ghdl_plugin_ok() if tc.present.get("yosys") else False
        _CACHE = tc
    return _CACHE

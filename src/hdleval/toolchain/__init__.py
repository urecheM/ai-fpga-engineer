"""HDL toolchain adapters (GHDL for compile/sim, Yosys for synthesis).

All adapters degrade gracefully: when a tool is absent the corresponding stage
returns a ``ToolResult`` with ``status='skipped'`` rather than failing, so the
pipeline runs end-to-end in any environment while CI (``HDLEVAL_REQUIRE_TOOLS=1``)
demands real tools.
"""

from __future__ import annotations

from .detect import Toolchain, ToolResult, detect
from .ghdl import compile_vhdl, simulate
from .yosys import synthesize

__all__ = [
    "ToolResult",
    "Toolchain",
    "compile_vhdl",
    "detect",
    "simulate",
    "synthesize",
]

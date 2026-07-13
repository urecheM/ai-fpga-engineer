"""Robustly pull a VHDL design out of a model completion.

Models wrap code in fenced blocks (```vhdl ... ```), sometimes with prose
around them, sometimes with multiple blocks. This module extracts the most
plausible design block and reports what it found so the harness can classify
"no code produced" separately from "code produced but wrong".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_FENCE_RE = re.compile(r"```(?:vhdl|vhd|VHDL)?\s*\n(.*?)```", re.DOTALL)
_ENTITY_RE = re.compile(r"\bentity\s+(\w+)\s+is", re.IGNORECASE)


@dataclass(frozen=True)
class ExtractedHDL:
    code: str
    entity: str | None
    n_blocks: int
    found: bool


def extract_vhdl(raw: str) -> ExtractedHDL:
    blocks = _FENCE_RE.findall(raw or "")
    if not blocks and _ENTITY_RE.search(raw or ""):
        # Fall back: maybe the whole message is code.
        blocks = [raw]
    if not blocks:
        return ExtractedHDL(code="", entity=None, n_blocks=0, found=False)

    # Prefer the block that actually declares an entity/architecture.
    chosen = max(
        blocks,
        key=lambda b: (bool(_ENTITY_RE.search(b)), "architecture" in b.lower(), len(b)),
    )
    m = _ENTITY_RE.search(chosen)
    entity = m.group(1) if m else None
    return ExtractedHDL(code=chosen.strip(), entity=entity, n_blocks=len(blocks), found=True)

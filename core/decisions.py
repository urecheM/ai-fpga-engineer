from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(frozen=True)
class ArchDecisions:
    opcode_encoding: str = "binary"
    register_output: bool = False
    share_add_sub: bool = False

    def label(self) -> str:
        bits = [self.opcode_encoding]
        if self.share_add_sub:
            bits.append("shared-add/sub")
        bits.append("registered" if self.register_output else "combinational")
        return ", ".join(bits)

    def key(self) -> str:
        return (f"{self.opcode_encoding}|reg={int(self.register_output)}"
                f"|share={int(self.share_add_sub)}")

    def with_(self, **changes: Any) -> "ArchDecisions":
        return replace(self, **changes)

    def to_dict(self) -> dict:
        return {"opcode_encoding": self.opcode_encoding,
                "register_output": self.register_output,
                "share_add_sub": self.share_add_sub}

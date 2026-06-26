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
@dataclass
class QoR:
    luts: int = 0
    registers: int = 0
    dsp: int = 0
    critical_path_ns: float = 0.0
    fmax_mhz: float = 0.0
    source: str = "estimated"         

    @property
    def area(self) -> int:
        return self.luts + self.registers

    def to_dict(self) -> dict:
        return {"luts": self.luts, "registers": self.registers, "dsp": self.dsp,
                "critical_path_ns": self.critical_path_ns,
                "fmax_mhz": self.fmax_mhz, "source": self.source}
@dataclass
class Targets:
    fmax_mhz: float | None = None
    max_luts: int | None = None
    max_registers: int | None = None
    def is_empty(self) -> bool:
        return self.fmax_mhz is None and self.max_luts is None and self.max_registers is None

    def unmet(self, q: QoR) -> list[str]:
        misses = []
        if self.fmax_mhz is not None and q.fmax_mhz < self.fmax_mhz:
            misses.append(f"Fmax {q.fmax_mhz:.0f} < target {self.fmax_mhz:.0f} MHz")
        if self.max_luts is not None and q.luts > self.max_luts:
            misses.append(f"LUTs {q.luts} > budget {self.max_luts}")
        if self.max_registers is not None and q.registers > self.max_registers:
            misses.append(f"registers {q.registers} > budget {self.max_registers}")
        return misses

    def met_by(self, q: QoR) -> bool:
        return not self.unmet(q)

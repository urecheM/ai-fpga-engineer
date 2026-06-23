from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any
#import json


@dataclass
class Port:
    name: str
    direction: str          # "in" | "out"
    width: int              # bits; 1 == std_logic, >1 == std_logic_vector
    role: str = "data"      # data | clock | reset | enable | opcode | flag | control
    description: str = ""

    @property
    def is_scalar(self) -> bool:
        return self.width == 1


@dataclass
class Operation:
    """One operation of a multi-function unit (e.g. an ALU function)."""
    name: str               # "ADD"
#    opcode: str             # "000"
    description: str = ""


@dataclass
class FunctionalRequirements:
    entity_name: str
    description: str
    design_class: str                           # alu | counter | register | comparator | unknown
    data_width: int = 8
#    ports: list[Port] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
#    operations: list[Operation] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
#    clocking: dict[str, Any] = field(default_factory=dict)   # {clock, reset, edge, ...}
#    constraints: dict[str, Any] = field(default_factory=dict)
#    assumptions: list[str] = field(default_factory=list)
    operations: list[Operation] = field(default_factory=list)
#    edge_cases: list[str] = field(default_factory=list)
#    verification_objectives: list[str] = field(default_factory=list)
#    source_request: str = ""
#    notes: list[str] = field(default_factory=list)

@dataclass
class FPGAPlatform:
    vendor: str = "generic"
    family: str = "generic"
    device: str = "generic"
    synthesis_tool: str = "generic"
    implementation_tool: str = "generic"

@dataclass
class TimingConstraints:
    target_frequency_mhz: float = 100.0
    max_latency_cycles: int | None = None
    clock_domains: list[str] = field(
        default_factory=lambda: ["clk"]
    )
    setup_margin_percent: float = 10.0
    hold_margin_percent: float = 5.0

    # --- convenience accessors -------------------------------------------
#    def inputs(self) -> list[Port]:
#        return [p for p in self.ports if p.direction == "in"]

#    def outputs(self) -> list[Port]:
#        return [p for p in self.ports if p.direction == "out"]

#    def port(self, name: str) -> Port | None:
#        for p in self.ports:
#            if p.name == name:
#                return p
#        return None

 #   def is_sequential(self) -> bool:
 #       return any(p.role in ("clock", "reset") for p in self.ports)

    # --- serialization ---------------------------------------------------
#    def to_dict(self) -> dict[str, Any]:
#        return asdict(self)

#    def to_json(self) -> str:
#        return json.dumps(self.to_dict(), indent=2)

#    @staticmethod
#    def from_dict(d: dict[str, Any]) -> "Specification":
#        d = dict(d)
#        d["ports"] = [Port(**p) for p in d.get("ports", [])]
#        d["operations"] = [Operation(**o) for o in d.get("operations", [])]
#        return Specification(**d)

"""Specification datamodel: the machine-readable record of *what* to build.

Produced by the requirements agent from the natural-language request and
consumed by every downstream stage. Deliberately small: ports, width, clocking,
operations, assumptions.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Port:
    name: str
    direction: str          # "in" | "out"
    width: int
    role: str               # clock | reset | enable | data | opcode | flag

    def to_dict(self) -> dict:
        return {"name": self.name, "direction": self.direction,
                "width": self.width, "role": self.role}


@dataclass
class Operation:
    name: str
    description: str = ""


@dataclass
class Specification:
    name: str
    title: str
    design_class: str                       # alu | counter | register | comparator | unknown
    data_width: int = 8
    clocking: str = "combinational"
    operations: list[Operation] = field(default_factory=list)
    ports: list[Port] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    source_request: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "title": self.title,
                "design_class": self.design_class, "data_width": self.data_width,
                "clocking": self.clocking,
                "operations": [o.name for o in self.operations],
                "ports": [p.to_dict() for p in self.ports],
                "assumptions": self.assumptions,
                "source_request": self.source_request}

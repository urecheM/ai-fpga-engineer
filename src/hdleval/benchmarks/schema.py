# Structured benchmark metadata
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ComplexityMetrics:
    state_complexity: int = 0
    arithmetic_complexity: int = 0
    concurrency: int = 0
    hierarchy_depth: int = 1
    timing_constraints: int = 0
    interface_count: int = 0
    control_complexity: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class Port:
    name: str
    direction: str
    width: int
    role: str = "data"


@dataclass(frozen=True)
class Benchmark:
    id: str
    version: str
    category: str
    title: str
    specification: str
    functional_requirements: list[str] = field(default_factory=list)
    expected_behavior: str = ""
    entity: str = ""
    interfaces: list[Port] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    complexity: ComplexityMetrics = field(default_factory=ComplexityMetrics)
    reference_hdl_path: str = ""
    testbench_path: str = ""
    testbench_entity: str = ""
    properties: list[str] = field(default_factory=list)
    estimated_difficulty: int = 0
    suite: str = ""

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["complexity"] = self.complexity.to_dict()
        d["interfaces"] = [asdict(p) for p in self.interfaces]
        return d

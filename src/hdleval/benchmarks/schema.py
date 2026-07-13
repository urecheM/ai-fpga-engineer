"""Structured benchmark metadata.

A benchmark is a *specification* plus everything needed to grade a solution:
functional requirements, expected interface, optional reference implementation,
verification assets, complexity metrics and taxonomy. Benchmarks are pure data
so the suite can be versioned and published independently (Hugging Face card).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ComplexityMetrics:
    """Objective inputs to difficulty scoring (see :mod:`difficulty`)."""

    state_complexity: int = 0  # number of FSM states
    arithmetic_complexity: int = 0  # distinct arithmetic ops / datapath width class
    concurrency: int = 0  # independent concurrent processes / channels
    hierarchy_depth: int = 1  # module nesting depth
    timing_constraints: int = 0  # clocked/timing requirements count
    interface_count: int = 0  # number of ports
    control_complexity: int = 0  # branches / handshake phases

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
    category: str  # arithmetic | fsm | communication | memory | processor | dsp | control
    title: str
    specification: str  # natural-language spec given to the model
    functional_requirements: list[str] = field(default_factory=list)
    expected_behavior: str = ""
    entity: str = ""
    interfaces: list[Port] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    complexity: ComplexityMetrics = field(default_factory=ComplexityMetrics)
    reference_hdl_path: str = ""  # relative to the benchmark dir
    testbench_path: str = ""
    testbench_entity: str = ""
    properties: list[str] = field(default_factory=list)
    estimated_difficulty: int = 0  # filled by difficulty_score if 0

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["complexity"] = self.complexity.to_dict()
        d["interfaces"] = [asdict(p) for p in self.interfaces]
        return d

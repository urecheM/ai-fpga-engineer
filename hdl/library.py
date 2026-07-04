from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
import math
import random

from ..core.spec import Specification, Port
from ..core.decisions import ArchDecisions, QoR

@dataclass
class TestPlan:
    kind: str
    vectors: list[dict]
    notes: list[str] = field(default_factory=list)

@dataclass
class GeneratedDesign:
    entity: str
    vhdl: str
    kind: str
    ports: list[Port]
    eval_fn: Callable | None
    run_fn: Callable | None
    default_plan: TestPlan
    resources: dict
    opcode_map: dict = field(default_factory=dict)
    decisions: ArchDecisions = field(default_factory=ArchDecisions)
    latency: int = 0 

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

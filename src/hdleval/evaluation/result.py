"""Result types produced by the evaluation harness."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class StageOutcome:
    stage: str
    status: str  # ok | fail | skipped
    duration_s: float = 0.0
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    benchmark: str
    category: str
    difficulty: int
    model: str
    prompt: str
    trial: int
    passed: bool = False
    failure_class: str = "none"
    stages: list[StageOutcome] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    hdl: str = ""
    retries: int = 0

    def stage(self, name: str) -> StageOutcome | None:
        for s in self.stages:
            if s.stage == name:
                return s
        return None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

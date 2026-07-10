"""Shared engineering context.

A single object that accumulates everything the pipeline learns about a design:
the specification, the chosen architecture and decisions, the design-space
exploration, critic findings, and the full verification / optimization / debug
histories, plus a per-stage confidence map. Every agent reads from and writes to
it, so the system builds knowledge over the run instead of resetting at each
stage, and the orchestrator can use confidence as a control signal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .decisions import ArchDecisions, QoR


@dataclass
class Candidate:
    """One point in the architecture design space, with its estimated QoR."""
    decisions: ArchDecisions
    qor: QoR
    selected: bool = False

    def to_dict(self) -> dict:
        return {"decisions": self.decisions.to_dict(), "qor": self.qor.to_dict(),
                "selected": self.selected}


@dataclass
class QoRIteration:
    iteration: int
    decisions: ArchDecisions
    qor: QoR
    action: str           # what optimization proposal was applied to get here
    met: bool

    def to_dict(self) -> dict:
        return {"iteration": self.iteration, "decisions": self.decisions.to_dict(),
                "qor": self.qor.to_dict(), "action": self.action, "met": self.met}


@dataclass
class EngineeringContext:
    decisions: ArchDecisions | None = None
    candidates: list[Candidate] = field(default_factory=list)
    qor: QoR | None = None
    qor_history: list[QoRIteration] = field(default_factory=list)
    confidence: dict[str, float] = field(default_factory=dict)   # stage -> [0,1]
    notes: list[str] = field(default_factory=list)

    # --- confidence ----------------------------------------------------
    def set_confidence(self, stage: str, value: float) -> None:
        self.confidence[stage] = round(max(0.0, min(1.0, value)), 3)

    def overall_confidence(self) -> float:
        if not self.confidence:
            return 0.0
        # the system is only as trustworthy as its weakest examined stage
        return round(min(self.confidence.values()), 3)

    def low_confidence_stages(self, threshold: float = 0.6) -> list[str]:
        return [s for s, c in self.confidence.items() if c < threshold]

    # --- serialization -------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "decisions": self.decisions.to_dict() if self.decisions else None,
            "candidates": [c.to_dict() for c in self.candidates],
            "qor": self.qor.to_dict() if self.qor else None,
            "qor_history": [q.to_dict() for q in self.qor_history],
            "confidence": self.confidence,
            "overall_confidence": self.overall_confidence(),
            "notes": self.notes,
        }

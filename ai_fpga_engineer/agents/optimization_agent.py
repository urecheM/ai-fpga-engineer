"""Optimization Agent.

Corrective, not advisory. Instead of emitting prose suggestions, it returns
machine-readable :class:`OptProposal` objects, each describing a concrete change
to the architecture decisions (register the output, switch opcode encoding,
share the add/sub adder, ...) together with the QoR that change is estimated to
achieve. The orchestrator applies a proposal by regenerating the RTL with the new
decisions, which is what closes the optimization loop. Estimates are heuristic
(pre-synthesis) and used for RANKING only; acceptance in the QoR loop uses
measured place-and-route numbers whenever the flow is available.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .base import Agent
from ..core.project import Project
from ..core.spec import Specification
from ..core.decisions import ArchDecisions, QoR, Targets, score
from ..hdl import library
from ..hdl.library import GeneratedDesign


@dataclass
class OptProposal:
    kind: str                         # short machine id, e.g. "register_output"
    rationale: str
    target_decisions: ArchDecisions
    decision_delta: dict              # fields that change vs the current design
    est_qor: QoR
    est_gain: str                     # human summary of the win

    def to_dict(self) -> dict:
        return {"kind": self.kind, "rationale": self.rationale,
                "decision_delta": self.decision_delta,
                "target_decisions": self.target_decisions.to_dict(),
                "est_qor": self.est_qor.to_dict(), "est_gain": self.est_gain}


@dataclass
class OptimizationReport:
    current: QoR
    explored: list[tuple[ArchDecisions, QoR]] = field(default_factory=list)
    proposals: list[OptProposal] = field(default_factory=list)
    best: str = ""

    def top(self) -> OptProposal | None:
        return self.proposals[0] if self.proposals else None


_RATIONALE = {
    "register_output": ("Register the function-unit outputs to add a pipeline "
                        "stage; isolates downstream timing and raises Fmax at the "
                        "cost of one cycle of latency."),
    "onehot_opcode": ("Switch opcode decoding to one-hot to flatten the result "
                      "multiplexer and shorten the decode path."),
    "share_add_sub": ("Implement ADD and SUB through one shared adder "
                      "(a + not(b) + 1), saving an adder's worth of LUTs."),
    "binary_opcode": "Use a compact binary opcode to minimise opcode port width.",
    "combinational_output": "Drop the output register to remove latency.",
}


class OptimizationAgent(Agent):
    name = "optimization"

    def run(self, project: Project, spec: Specification, design: GeneratedDesign,
            objective: str = "balanced", targets: Targets | None = None) -> OptimizationReport:
        targets = targets or Targets()
        current = _qor(design)
        explored = [(c, library.estimate(spec, c)) for c in library.candidate_decisions(spec)]
        proposals = self.propose(spec, design.decisions, current, objective, targets)

        best_dec, _ = max(explored, key=lambda cq: score(cq[1], objective))
        report = OptimizationReport(current, explored, proposals, best_dec.label())
        self._write(project, design, report, objective, targets)
        msg = (f"{current.luts} LUTs, {current.registers} regs, Fmax≈{current.fmax_mhz} MHz; "
               f"{len(proposals)} actionable proposal(s)")
        self.log(project, msg, "success")
        project.metrics["resources"] = current.to_dict()
        return report

    # ------------------------------------------------------------------
    def propose(self, spec: Specification, current: ArchDecisions, current_qor: QoR,
                objective: str, targets: Targets) -> list[OptProposal]:
        """Rank concrete decision changes that improve on the current design."""
        out: list[OptProposal] = []
        cur_score = score(current_qor, objective)
        for cand in library.candidate_decisions(spec):
            if cand.key() == current.key():
                continue
            q = library.estimate(spec, cand)
            delta = {k: v for k, v in cand.to_dict().items()
                     if v != current.to_dict()[k]}
            if not delta:
                continue
            kind = self._delta_kind(delta)
            # accept if it improves the objective, or if it helps meet an unmet target
            helps_target = bool(targets.unmet(current_qor)) and not targets.unmet(q)
            if score(q, objective) > cur_score + 1e-9 or helps_target:
                out.append(OptProposal(
                    kind=kind, rationale=_RATIONALE.get(kind, "architecture change"),
                    target_decisions=cand, decision_delta=delta, est_qor=q,
                    est_gain=self._gain(current_qor, q)))
        out.sort(key=lambda p: score(p.est_qor, objective), reverse=True)
        return out

    @staticmethod
    def _delta_kind(delta: dict) -> str:
        if "register_output" in delta:
            return "register_output" if delta["register_output"] else "combinational_output"
        if "opcode_encoding" in delta:
            return "onehot_opcode" if delta["opcode_encoding"] == "onehot" else "binary_opcode"
        if "share_add_sub" in delta:
            return "share_add_sub" if delta["share_add_sub"] else "split_add_sub"
        return "architecture_change"

    @staticmethod
    def _gain(a: QoR, b: QoR) -> str:
        df = b.fmax_mhz - a.fmax_mhz
        da = b.area - a.area
        parts = []
        if abs(df) >= 0.1:
            parts.append(f"Fmax {'+' if df>=0 else ''}{df:.0f} MHz")
        if da != 0:
            parts.append(f"area {'+' if da>=0 else ''}{da} cells")
        return ", ".join(parts) or "no net change"

    def _write(self, project, design, report: OptimizationReport,
               objective: str, targets: Targets) -> None:
        lines = [f"# Optimization Report — {design.entity}",
                 f"\nObjective: **{objective}**. Targets: "
                 f"{'none' if targets.is_empty() else targets}. "
                 "Estimates are heuristic (pre-synthesis) and used for ranking; "
                 "acceptance uses measured numbers when the flow is present "
                 "(see docs/CLAIMS.md).\n",
                 "## Explored design space",
                 "| architecture | LUTs | regs | Fmax (MHz) |",
                 "|--------------|------|------|------------|"]
        for dec, q in report.explored:
            star = " *" if dec.label() == report.best else ""
            lines.append(f"| {dec.label()}{star} | {q.luts} | {q.registers} | {q.fmax_mhz} |")
        lines.append("\n## Actionable proposals (ranked)")
        if report.proposals:
            lines.append("| change | est. gain | rationale |")
            lines.append("|--------|-----------|-----------|")
            for p in report.proposals:
                lines.append(f"| `{p.kind}` | {p.est_gain} | {p.rationale} |")
        else:
            lines.append("Current architecture is already best for this objective.")
        project.write(f"docs/{design.entity}_optimization.md", "\n".join(lines), "optimization")
        project.write(f"reports/{design.entity}_metrics.json",
                      json.dumps({"current": report.current.to_dict(),
                                  "explored": [{"decisions": d.to_dict(), "qor": q.to_dict()}
                                               for d, q in report.explored],
                                  "proposals": [p.to_dict() for p in report.proposals]},
                                 indent=2))


def _qor(design: GeneratedDesign) -> QoR:
    r = design.resources
    return QoR(r.get("luts", 0), r.get("registers", 0), r.get("dsp", 0),
               r.get("critical_path_ns", 1.0), r.get("fmax_mhz", 0.0), "estimated")

"""HDL Generation Agent: emits synthesizable VHDL + design notes from the
architecture decisions chosen upstream."""
from __future__ import annotations

from .base import Agent
from ..core.project import Project
from ..core.spec import Specification
from ..core.decisions import ArchDecisions
from ..hdl import library
from ..hdl.library import GeneratedDesign


class HDLAgent(Agent):
    name = "hdl"

    def run(self, project: Project, spec: Specification,
            decisions: ArchDecisions | None = None) -> GeneratedDesign:
        decisions = decisions or ArchDecisions()
        design = library.generate(spec, decisions)
        project.write(f"rtl/{design.entity}.vhd", design.vhdl, "rtl")
        self.log(project, f"generated rtl/{design.entity}.vhd "
                          f"({len(design.vhdl.splitlines())} lines) "
                          f"[{decisions.label()}]", "success")

        notes = self._notes(spec, design)
        project.write(f"docs/{design.entity}_design_notes.md", notes, "design_notes")
        if design.opcode_map:
            self.log(project, "opcode map: " +
                     ", ".join(f"{k}={v}" for k, v in design.opcode_map.items()))
        return design

    def _notes(self, spec: Specification, design: GeneratedDesign) -> str:
        lines = [f"# Design Notes — {spec.title}", "",
                 f"- Entity: `{design.entity}`",
                 f"- Class: {spec.design_class} ({design.kind})",
                 f"- Architecture: {design.decisions.label()}",
                 f"- Output latency: {design.latency} clock(s)",
                 f"- Data width: {spec.data_width}", "",
                 "## Ports", "", "| name | dir | width | role |",
                 "|------|-----|-------|------|"]
        for p in design.ports:
            lines.append(f"| `{p.name}` | {p.direction} | {p.width} | {p.role} |")
        if design.opcode_map:
            lines += ["", "## Opcode encoding "
                      f"({design.decisions.opcode_encoding})", "",
                      "| op | code |", "|----|------|"]
            for k, v in design.opcode_map.items():
                lines.append(f"| {k} | `{v}` |")
        lines += ["", "## Assumptions"]
        lines += [f"- {a}" for a in spec.assumptions] or ["- (none)"]
        return "\n".join(lines)

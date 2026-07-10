"""Architecture agent: proposes the implementation approach for a specification.

Rule-based: each design class has a known-good architectural pattern; the
binding, machine-readable half of the architecture (ArchDecisions) is chosen
by design-space exploration in the orchestrator — this agent supplies the
human-readable intent the critic reviews and the report documents. On critic
revision requests it records what changed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .base import Agent
from ..core.spec import Specification

_STYLES = {
    "alu": ("combinational function unit",
            "Opcode-decoded result multiplexer over parallel function blocks; "
            "flags derived from the selected result. The binding decisions "
            "(opcode encoding, output registering, add/sub sharing) are chosen "
            "by design-space exploration and consumed directly by the generator.",
            ["opcode decoder", "function blocks", "result mux", "flag logic"]),
    "comparator": ("combinational magnitude comparator",
                   "Parallel unsigned relational network producing one-hot "
                   "gt/eq/lt; optional output registering per the decision contract.",
                   ["magnitude network", "flag encode"]),
    "counter": ("synchronous datapath",
                "Single always-clocked process: synchronous active-high reset, "
                "enable-gated increment, combinational terminal-count decode.",
                ["state register", "increment logic", "tc decode"]),
    "register": ("synchronous datapath",
                 "Single always-clocked process: synchronous reset dominates, "
                 "enable-gated load, hold otherwise.",
                 ["state register", "load/hold mux"]),
}


@dataclass
class Architecture:
    style: str
    summary: str
    blocks: list[str] = field(default_factory=list)
    revision: int = 0


class ArchitectureAgent(Agent):
    name = "architecture"

    def run(self, project, spec: Specification, revision: int = 0) -> Architecture:
        style, summary, blocks = _STYLES.get(
            spec.design_class,
            ("unknown", "No architectural pattern is known for this class; the "
             "request was classified 'unknown' and is reported, not generated.", []))
        if revision:
            summary += (f" (revision {revision}: adjusted after design-review "
                        "findings.)")
        arch = Architecture(style, summary, blocks, revision)
        project.write(f"docs/{spec.name}_architecture.md",
                      f"# Architecture — {spec.title}\n\n{summary}\n\n"
                      f"- Style: {style}\n- Blocks: {', '.join(blocks) or '(n/a)'}\n",
                      "architecture_doc")
        self.log(project, f"proposed: {style}", "success")
        return arch

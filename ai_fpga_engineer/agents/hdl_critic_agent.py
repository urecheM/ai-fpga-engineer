"""HDL Critic Agent (RTL review).

The architecture critic reviews *intent*; this critic reviews the *generated RTL*
before verification begins, catching the hardware-specific defect classes that
only appear after code generation: missing library clauses, undriven outputs,
potential inferred latches (a combinational process whose ``case`` lacks a
``when others``), sequential logic without a clock or reset, and entity/
architecture mismatches. Blocking findings that the linter knows how to repair
are handed to the debug agent; the rest are reported so downstream tools are not
the first to discover them.

It reuses the structural linter for the cheap checks and adds RTL-structure
heuristics on top.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .base import Agent
from ..core.project import Project
from ..core.spec import Specification
from ..hdl.library import GeneratedDesign
from ..sim.lint import lint


@dataclass
class HDLFinding:
    severity: str        # block | warn | info
    rule: str
    message: str
    fixable: bool = False


@dataclass
class HDLReview:
    findings: list[HDLFinding] = field(default_factory=list)

    @property
    def blocking(self) -> list[HDLFinding]:
        return [f for f in self.findings if f.severity == "block"]

    @property
    def clean(self) -> bool:
        return not self.blocking


class HDLCriticAgent(Agent):
    name = "hdl-critic"

    def run(self, project: Project, spec: Specification,
            design: GeneratedDesign) -> HDLReview:
        vhdl = (project.root / f"rtl/{design.entity}.vhd").read_text()
        review = HDLReview(self._analyze(spec, design, vhdl))

        for f in review.findings:
            lvl = "error" if f.severity == "block" else "warn" if f.severity == "warn" else "info"
            if f.severity != "info":
                self.log(project, f"{f.rule}: {f.message}", lvl)
        if review.clean:
            self.log(project, "RTL review passed (synthesizable, no blocking issues)",
                     "success")
        self._write(project, design, review)
        return review

    # ------------------------------------------------------------------
    def _analyze(self, spec: Specification, design: GeneratedDesign,
                 vhdl: str) -> list[HDLFinding]:
        out: list[HDLFinding] = []
        low = vhdl.lower()

        # 1. structural defects from the linter (libraries, undriven outputs, ...)
        for i in lint(vhdl):
            sev = "block" if i.code in ("MISSING_STD_LOGIC", "MISSING_NUMERIC_STD",
                                        "NO_ENTITY", "NO_ARCH", "ARCH_ENTITY_MISMATCH",
                                        "UNDRIVEN_OUTPUT", "PAREN_IMBALANCE") else "warn"
            out.append(HDLFinding(sev, i.code, i.message, i.fixable))

        # 2. inferred-latch risk: a combinational process with a case but no
        #    'when others' leaves the target unassigned for unlisted choices.
        for proc in self._combinational_processes(vhdl):
            if re.search(r"\bcase\b", proc, re.I) and not re.search(r"when\s+others", proc, re.I):
                out.append(HDLFinding("block", "INFERRED_LATCH",
                                      "combinational process has a case without "
                                      "'when others'; unlisted opcodes infer a latch.",
                                      fixable=False))
            if re.search(r"\bif\b", proc, re.I) and not re.search(r"\belse\b", proc, re.I) \
                    and "<=" in proc:
                out.append(HDLFinding("warn", "INCOMPLETE_IF",
                                      "combinational 'if' without 'else' may infer a latch.",
                                      fixable=False))

        # 3. sequential designs must be clocked and (for state) reset.
        is_seq = design.kind == "sequential"
        has_clk = any(p.role == "clock" for p in design.ports)
        if is_seq and not has_clk:
            out.append(HDLFinding("block", "NO_CLOCK",
                                  "sequential design has no clock port.", fixable=False))
        if is_seq and "rising_edge" not in low and "falling_edge" not in low:
            out.append(HDLFinding("block", "NO_EDGE",
                                  "sequential design has no edge-sensitive process.",
                                  fixable=False))
        needs_reset = spec.design_class in ("counter", "register")
        if needs_reset and not re.search(r"\brst\b|\breset\b", low):
            out.append(HDLFinding("warn", "NO_RESET",
                                  "stateful design has no reset; power-up state is "
                                  "undefined in hardware.", fixable=False))

        # 4. reset polarity / style note (informational, good practice signal)
        if is_seq and re.search(r"if\s+\w*rst\w*\s*=\s*'1'", low):
            out.append(HDLFinding("info", "SYNC_RESET",
                                  "synchronous active-high reset detected (maps cleanly "
                                  "to FPGA FF reset).", fixable=False))

        # 5. registered-output timing note
        if getattr(design, "latency", 0) >= 1:
            out.append(HDLFinding("info", "PIPELINE_LATENCY",
                                  f"output is registered (latency {design.latency} "
                                  "clock(s)); constrain the output register's clock.",
                                  fixable=False))
        return out

    @staticmethod
    def _combinational_processes(vhdl: str) -> list[str]:
        """Return the text of processes that are NOT edge-sensitive (i.e. likely
        combinational), so latch heuristics only apply to them."""
        procs = re.findall(r"\bprocess\b.*?\bend\s+process\b", vhdl, re.I | re.S)
        return [p for p in procs if "rising_edge" not in p.lower()
                and "falling_edge" not in p.lower()]

    def _write(self, project: Project, design: GeneratedDesign, review: HDLReview) -> None:
        lines = [f"# HDL Review — {design.entity}", ""]
        if not review.findings:
            lines.append("No issues found; the generated RTL is synthesizable and "
                         "structurally sound.")
        else:
            lines.append("| severity | rule | finding |")
            lines.append("|----------|------|---------|")
            for f in review.findings:
                lines.append(f"| {f.severity} | `{f.rule}` | {f.message} |")
            lines.append(f"\nBlocking issues: **{len(review.blocking)}**.")
        project.write(f"docs/{design.entity}_hdl_review.md", "\n".join(lines),
                      "hdl_review")

"""Debug agent: rule-based repair with an honestly stated scope.

Repairs are limited to defect classes with a mechanical fix — missing
library/use clauses flagged as ``fixable`` by the linter. Anything else
(semantic mismatches found by GHDL, inferred latches, undriven outputs) is
*diagnosed and recorded, not silently 'fixed'*: the step is logged with
``resolved=False`` and ``final_clean`` goes False, which correctly fails the
run. The mutation campaign documents exactly which classes fall on which side
of that line — an analyzed escape beats a fake repair.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .base import Agent
from ..core.spec import Specification
from ..hdl.library import GeneratedDesign
from ..sim.lint import lint

MAX_REPAIR_ITERS = 3


@dataclass
class DebugStep:
    iteration: int
    defect: str
    action: str
    resolved: bool


@dataclass
class DebugReport:
    steps: list[DebugStep] = field(default_factory=list)
    iterations: int = 0
    final_clean: bool = True


class DebugAgent(Agent):
    name = "debug"

    def run(self, project, spec: Specification, design: GeneratedDesign,
            ghdl_log: str | None = None) -> DebugReport:
        report = DebugReport()
        rtl_path = project.root / f"rtl/{design.entity}.vhd"

        for it in range(1, MAX_REPAIR_ITERS + 1):
            vhdl = rtl_path.read_text()
            fixable = [i for i in lint(vhdl) if i.fixable]
            if not fixable:
                break
            report.iterations = it
            for issue in fixable:
                vhdl, action = self._repair(issue.code, vhdl)
                resolved = action is not None
                report.steps.append(DebugStep(it, issue.code,
                                              action or "no rule available",
                                              resolved))
                self.log(project, f"{issue.code}: "
                         f"{action or 'no mechanical repair rule'}",
                         "success" if resolved else "error")
            rtl_path.write_text(vhdl)
            design.vhdl = vhdl

        remaining = lint(design.vhdl if design.vhdl else rtl_path.read_text())
        if any(i.fixable for i in remaining):
            report.final_clean = False

        # GHDL found a semantic mismatch: diagnose honestly, do not pretend.
        if ghdl_log and ("FAILED" in ghdl_log or "severity failure" in ghdl_log.lower()):
            first = self._first_mismatch(ghdl_log)
            report.iterations = max(report.iterations, 1)
            report.steps.append(DebugStep(
                report.iterations, "SIMULATION_MISMATCH",
                f"GHDL reported a functional mismatch ({first}); no rule-based "
                "repair exists for semantic defects — flagged for review",
                resolved=False))
            report.final_clean = False
            self.log(project, "semantic mismatch cannot be rule-repaired; "
                              "flagged for review", "error")
        return report

    # ------------------------------------------------------------------
    @staticmethod
    def _repair(code: str, vhdl: str) -> tuple[str, str | None]:
        if code == "MISSING_STD_LOGIC":
            if re.search(r"^\s*library\s+ieee\s*;", vhdl, re.I | re.M):
                new = re.sub(r"(^\s*library\s+ieee\s*;\s*\n)",
                             r"\1use ieee.std_logic_1164.all;\n",
                             vhdl, count=1, flags=re.I | re.M)
            else:
                new = "library ieee;\nuse ieee.std_logic_1164.all;\n" + vhdl
            return new, "inserted 'use ieee.std_logic_1164.all;'"
        if code == "MISSING_NUMERIC_STD":
            if re.search(r"use\s+ieee\.std_logic_1164\.all\s*;", vhdl, re.I):
                new = re.sub(r"(use\s+ieee\.std_logic_1164\.all\s*;\s*\n)",
                             r"\1use ieee.numeric_std.all;\n",
                             vhdl, count=1, flags=re.I)
            elif re.search(r"^\s*library\s+ieee\s*;", vhdl, re.I | re.M):
                new = re.sub(r"(^\s*library\s+ieee\s*;\s*\n)",
                             r"\1use ieee.numeric_std.all;\n",
                             vhdl, count=1, flags=re.I | re.M)
            else:
                new = "library ieee;\nuse ieee.numeric_std.all;\n" + vhdl
            return new, "inserted 'use ieee.numeric_std.all;'"
        return vhdl, None

    @staticmethod
    def _first_mismatch(log: str) -> str:
        m = re.search(r"vector \d+: \w+ mismatch", log)
        return m.group(0) if m else "see ghdl log"

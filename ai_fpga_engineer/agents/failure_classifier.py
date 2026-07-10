"""Failure classification (pre-debug triage).

A syntax error, an assertion mismatch, a timing violation, and a resource
overflow demand very different responses. Before the debugger runs, this module
inspects the available evidence — lint issues, the reference-model property
result, the simulation log, and QoR vs. targets — and assigns a failure
*category* plus a recommended repair strategy. The debugger and orchestrator use
the category to pick a targeted action instead of one generic fix.
"""
from __future__ import annotations

from dataclasses import dataclass

# category -> default repair strategy the orchestrator/debugger should pursue
STRATEGY = {
    "compilation": "code correction (insert missing clauses / fix syntax), then re-elaborate",
    "assertion":   "logic/property fix: re-examine the function unit against the golden model",
    "simulation":  "inspect the failing vector, repair the offending logic, re-simulate",
    "timing":      "pipeline / retime: register the critical path (set register_output)",
    "resource":    "reduce area: share datapath resources (set share_add_sub) or simplify",
    "architectural": "revise architecture decisions and regenerate",
    "none":        "no action required",
}


@dataclass
class FailureClass:
    category: str
    detail: str

    @property
    def strategy(self) -> str:
        return STRATEGY.get(self.category, STRATEGY["none"])


def classify(*, lint_codes: list[str] | None = None,
             property_failures: list[str] | None = None,
             sim_ran: bool = False, sim_passed: bool | None = None,
             sim_log: str | None = None,
             qor_unmet: list[str] | None = None) -> FailureClass:
    """Return the most actionable failure category given the evidence.

    Precedence: compilation defects first (nothing else runs until RTL elaborates),
    then assertion/simulation failures, then unmet timing/area targets.
    """
    lint_codes = lint_codes or []
    property_failures = property_failures or []
    qor_unmet = qor_unmet or []
    low = (sim_log or "").lower()

    # 1. compilation / elaboration
    compile_codes = {"MISSING_STD_LOGIC", "MISSING_NUMERIC_STD", "NO_ENTITY",
                     "NO_ARCH", "ARCH_ENTITY_MISMATCH", "PAREN_IMBALANCE"}
    if compile_codes.intersection(lint_codes):
        hit = ", ".join(sorted(compile_codes.intersection(lint_codes)))
        return FailureClass("compilation", f"structural/library defect(s): {hit}")
    if any(k in low for k in ("syntax error", "no declaration", "compilation error",
                              "cannot elaborate")):
        return FailureClass("compilation", "compiler reported a syntax/elaboration error")

    # 2. functional failures
    if property_failures:
        return FailureClass("assertion",
                            f"{len(property_failures)} reference-model property "
                            f"violation(s): {property_failures[0]}")
    if sim_ran and sim_passed is False:
        if "severity failure" in low or "mismatch" in low or "vector(s) failed" in low \
                or "cycle(s) failed" in low:
            return FailureClass("simulation", "self-checking testbench reported a mismatch")
        return FailureClass("simulation", "simulation failed (see log)")

    # 3. structural latch/undriven issues that are not strictly compile-blocking
    if "INFERRED_LATCH" in lint_codes or "UNDRIVEN_OUTPUT" in lint_codes:
        return FailureClass("architectural",
                            "inferred latch / undriven output indicates a structural defect")

    # 4. QoR closure misses
    if qor_unmet:
        miss = qor_unmet[0].lower()
        if "fmax" in miss:
            return FailureClass("timing", qor_unmet[0])
        if "lut" in miss or "register" in miss:
            return FailureClass("resource", qor_unmet[0])
        return FailureClass("timing", qor_unmet[0])

    return FailureClass("none", "no failure detected")

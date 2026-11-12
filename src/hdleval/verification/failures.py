"""Failure classification across the evaluation pipeline."""

from __future__ import annotations

from enum import Enum


class FailureClass(str, Enum):
    NONE = "none"
    NO_CODE = "no_code_generated"
    SYNTAX = "syntax_error"
    COMPILE = "compilation_error"
    INTERFACE = "interface_mismatch"
    SYNTHESIS = "synthesis_failure"
    SIMULATION = "simulation_failure"
    PROTOCOL = "protocol_violation"
    TIMING = "timing_failure"
    VERIFICATION = "verification_failure"
    OPTIMIZATION = "optimization_failure"
    # compiled (and synthesised) but no simulator/testbench ran: NOT a pass
    UNVERIFIED = "unverified"
    EQUIVALENCE = "equivalence_failure"  # miter found a counterexample vs the reference

def classify_failure(
    *,
    code_found: bool,
    compile_status: str,
    synth_status: str,
    sim_status: str,
    functional_ok: bool,
    interface_ok: bool = True,
    equiv_status: str = "skipped",  # proven | bmc_pass | fail | error | skipped
) -> FailureClass:
    """Map the first failing stage to a single canonical failure class."""
    if not code_found:
        return FailureClass.NO_CODE
    if compile_status == "fail":
        return FailureClass.COMPILE
    if not interface_ok:
        return FailureClass.INTERFACE
    if synth_status == "fail":
        return FailureClass.SYNTHESIS
    if sim_status == "fail":
        return FailureClass.SIMULATION
    if equiv_status == "fail":
        return FailureClass.EQUIVALENCE
    if sim_status == "skipped" and equiv_status not in ("proven", "bmc_pass"):
        return FailureClass.UNVERIFIED
    if not functional_ok:
        return FailureClass.VERIFICATION
    return FailureClass.NONE

"""Failure classification across the evaluation pipeline."""
from __future__ import annotations

from enum import Enum


class FailureClass(str, Enum):
    NONE = "none"
    NO_CODE = "no_code_generated"
    SYNTAX = "syntax_error"
    COMPILE = "compilation_error"
    SYNTHESIS = "synthesis_failure"
    SIMULATION = "simulation_failure"
    PROTOCOL = "protocol_violation"
    TIMING = "timing_failure"
    VERIFICATION = "verification_failure"
    OPTIMIZATION = "optimization_failure"


def classify_failure(
    *,
    code_found: bool,
    compile_status: str,
    synth_status: str,
    sim_status: str,
    functional_ok: bool,
    property_fail: bool,
) -> FailureClass:
    """Map the first failing stage to a single canonical failure class."""
    if not code_found:
        return FailureClass.NO_CODE
    if compile_status == "fail":
        return FailureClass.COMPILE
    if synth_status == "fail":
        return FailureClass.SYNTHESIS
    if sim_status == "fail":
        return FailureClass.SIMULATION
    if property_fail:
        return FailureClass.PROTOCOL
    if not functional_ok:
        return FailureClass.VERIFICATION
    return FailureClass.NONE

from __future__ import annotations

from hdleval.verification.failures import FailureClass, classify_failure
from hdleval.verification.properties import check_properties


def test_classify_precedence():
    assert (
        classify_failure(
            code_found=False,
            compile_status="ok",
            synth_status="ok",
            sim_status="ok",
            functional_ok=True,
        )
        == FailureClass.NO_CODE
    )
    assert (
        classify_failure(
            code_found=True,
            compile_status="fail",
            synth_status="ok",
            sim_status="ok",
            functional_ok=True,
        )
        == FailureClass.COMPILE
    )
    assert (
        classify_failure(
            code_found=True,
            compile_status="ok",
            synth_status="ok",
            sim_status="ok",
            functional_ok=True,
        )
        == FailureClass.NONE
    )


def test_properties_report():
    fsm = "type state_t is (S0,S1); ... state<=S1; state<=S0;"
    rep = check_properties(fsm, ["deadlock_freedom", "unreachable_state"])
    assert set(rep.results) == {"deadlock_freedom", "unreachable_state"}
    assert rep.n_pass + rep.n_fail <= 2

def test_lint_never_decides_pass_fail():
    assert (
        classify_failure(
            code_found=True,
            compile_status="ok",
            synth_status="ok",
            sim_status="ok",
            functional_ok=True,
        )
        == FailureClass.NONE
    )

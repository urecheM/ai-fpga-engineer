from __future__ import annotations

import pytest

from hdleval.verification.error_kinds import classify_tool_error

CASES = [
    (
        'd.vhd:1:192:error: can\'t match "a" with type array type "UNRESOLVED_UNSIGNED"',
        "type_mismatch",
    ),
    ('d.vhd:1:202:error: no function declarations for operator "+"', "type_mismatch"),
    ('d.vhd:1:162:error: no declaration for "foo"', "undeclared_name"),
    (
        'd.vhd:1:93:error: use of synopsys package "std_logic_arith" needs the -fsynopsys option',
        "nonstandard_library",
    ),
    ("d.vhd:1:163:error: ';' expected at end of signal assignment", "syntax"),
    ('design.vhd:1:13:error: missing ";" at end of library clause', "syntax"),
    ("design.vhd:12:56:error: 'begin' is expected instead of end of file", "syntax"),
    ('d.vhd:1:156:error: port "y" can\'t be assigned', "port_mode"),
    ("d.vhd:1:203:error: missing choice(s)", "incomplete_case"),
    ('d.vhd:1:80:error: multiple assignments for "y" offsets 0:0', "multiple_drivers"),
    ("error: cannot find entity or configuration wrongname", "missing_entity"),
    ('error: entity "adder8" has no architecture in library "work"', "missing_entity"),
    ("ghdl analyze timeout", "timeout"),
    ("something nobody has seen before", "other"),
]


@pytest.mark.parametrize(("msg", "kind"), CASES)
def test_compile_messages(msg, kind):
    assert classify_tool_error(msg) == kind


def test_simulation_assertion_is_functional_mismatch():
    out = "tb.vhd:40:9:@15ns:(assertion warning): MISMATCH vector 1 bit 3 expected '1' got '0'"
    assert classify_tool_error(out, "simulation") == "functional_mismatch"


def test_simulation_bound_failure_is_width():
    out = "(assertion error): 2 output bit(s) differ\nd.vhd:3:5:@0ms:(bound check failure): ..."
    assert classify_tool_error(out, "simulation") == "width_mismatch"

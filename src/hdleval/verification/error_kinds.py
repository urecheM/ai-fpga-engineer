"""Sub-classify toolchain failures by message, so "57 compile errors" becomes a
breakdown of *what* models get wrong in VHDL.

Patterns were taken from real GHDL (analysis/elaboration/runtime) and
Yosys+ghdl-plugin (synthesis) output. Rules are checked in order and the first
match wins, so specific rules come before the generic ``syntax`` rule. Unknown
messages fall into ``other``; inspect those periodically and add rules.
"""

from __future__ import annotations

import re

# (kind, pattern) - order matters
_RULES: list[tuple[str, str]] = [
    ("nonstandard_library", r"synopsys package|std_logic_(arith|unsigned|signed)"),
    ("undeclared_name", r"no declaration for"),
    (
        "multiple_drivers",
        r"multiple assignments for|several sources for|multiple conflicting drivers",
    ),
    ("port_mode", r"can't be (assigned|read)|port \"?\w+\"? .*mode"),
    ("incomplete_case", r"missing choice"),
    (
        "width_mismatch",
        r"value constraints don't match|bound check failure|length of value does not match"
        r"|length mismatch|index .* out of range",
    ),
    (
        "type_mismatch",
        r"can't match|no function declarations for operator|no overloaded|type of .* does not match"
        r"|incompatible|is not compatible|cannot be converted|no matching",
    ),
    (
        "missing_entity",
        r"cannot find entity|unit \"?\w+\"? not found|entity .* not found|has no architecture",
    ),
    ("combinational_loop", r"logic loop|combinatorial loop|latch"),
    ("timeout", r"timeout"),
    (
        "syntax",
        r"expected|unexpected|identifier is expected|parse error|syntax error|extra ';'"
        r"|missing \"?[;,()]|end of file",
    ),
]
_COMPILED = [(k, re.compile(p, re.IGNORECASE)) for k, p in _RULES]

KINDS = [k for k, _ in _RULES] + ["functional_mismatch", "other"]


def error_lines(text: str) -> list[str]:
    """Lines that report an error (warnings are ignored unless nothing else is)."""
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    errs = [ln for ln in lines if re.search(r"error|failure", ln, re.I)]
    return errs or lines


def classify_tool_error(text: str, stage: str = "compile") -> str:
    """Map raw tool output to one error kind (first matching rule on error lines)."""
    lines = error_lines(text)
    if stage == "simulation" and re.search(r"MISMATCH|assertion (error|failure)", text or ""):
        # a testbench assertion: the design ran but produced wrong values, unless
        # the runtime reported a more specific cause below
        for kind, rx in _COMPILED:
            if kind in ("width_mismatch",) and any(rx.search(ln) for ln in lines):
                return kind
        return "functional_mismatch"
    for kind, rx in _COMPILED:
        if any(rx.search(ln) for ln in lines):
            return kind
    return "other"
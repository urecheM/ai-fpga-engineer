"""Classify a failure and synthesise a corrective instruction for regeneration."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Diagnosis:
    failure_class: str
    summary: str
    corrective_hint: str


_PATTERNS = [
    (
        r"syntax error|parse error|unexpected",
        "syntax_error",
        "Fix the VHDL syntax error; ensure entity/architecture are well-formed.",
    ),
    (
        r"no declaration|not declared|unknown identifier",
        "compilation_error",
        "Declare all signals/ports referenced; check names and libraries.",
    ),
    (
        r"type .*mismatch|cannot match|incompatible types",
        "compilation_error",
        "Resolve type mismatches; align std_logic_vector widths and use numeric_std.",
    ),
    (
        r"assertion .*failure|expected .* got",
        "verification_failure",
        "The logic is wrong for some inputs; re-derive the truth table / next-state.",
    ),
    (
        r"multiple .*driver|multiply driven",
        "protocol_violation",
        "Give every signal exactly one driver; move logic into a single process.",
    ),
]


def diagnose(stderr: str, failure_class: str = "") -> Diagnosis:
    text = (stderr or "").lower()
    for pat, cls, hint in _PATTERNS:
        if re.search(pat, text):
            return Diagnosis(
                failure_class=failure_class or cls, summary=stderr[:200], corrective_hint=hint
            )
    return Diagnosis(
        failure_class=failure_class or "unknown",
        summary=stderr[:200],
        corrective_hint="Review the design against the specification and regenerate.",
    )

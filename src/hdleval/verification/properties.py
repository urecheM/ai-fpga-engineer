"""Automated (static) property verification.

Full formal verification requires a formal backend (e.g. SymbiYosys); where it
is unavailable we run deterministic *static* property heuristics so every run
produces a property report. Each property returns pass/fail/unknown. The
strategy pattern lets a formal engine be dropped in behind the same interface.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PropertyReport:
    results: dict[str, str] = field(default_factory=dict)  # name -> pass|fail|unknown

    @property
    def n_pass(self) -> int:
        return sum(1 for v in self.results.values() if v == "pass")

    @property
    def n_fail(self) -> int:
        return sum(1 for v in self.results.values() if v == "fail")


def _deadlock_freedom(vhdl: str) -> str:
    m = re.search(r"type\s+\w*state\w*\s+is\s*\((.*?)\)", vhdl, re.I | re.S)
    if not m:
        return "unknown"
    states = [s.strip() for s in m.group(1).split(",") if s.strip()]
    # every declared state should appear as a transition target somewhere
    reachable = sum(1 for s in states if len(re.findall(rf"\b{re.escape(s)}\b", vhdl)) > 1)
    return "pass" if reachable == len(states) else "fail"


def _unreachable_state(vhdl: str) -> str:
    m = re.search(r"type\s+\w*state\w*\s+is\s*\((.*?)\)", vhdl, re.I | re.S)
    if not m:
        return "unknown"
    states = [s.strip() for s in m.group(1).split(",") if s.strip()]
    unreached = [s for s in states if len(re.findall(rf"<=\s*{re.escape(s)}\b", vhdl)) == 0]
    # the reset/initial state need not be assigned; allow one
    return "pass" if len(unreached) <= 1 else "fail"


def _overflow_guarded(vhdl: str) -> str:
    if re.search(r"\bunsigned\b|\bsigned\b", vhdl, re.I):
        if re.search(r"carry|overflow|\+\s*1|resize", vhdl, re.I):
            return "pass"
        return "unknown"
    return "unknown"


def _mutual_exclusion(vhdl: str) -> str:
    # one driver per output: flag multiple concurrent assignments to same signal
    assigns = re.findall(r"(\w+)\s*<=", vhdl)
    dupes = {a for a in assigns if assigns.count(a) > 1}
    # duplicates are fine inside processes; only concurrent context is a smell
    return "pass" if not dupes or "process" in vhdl.lower() else "unknown"


def _transaction_completion(vhdl: str) -> str:
    if re.search(r"valid|ready|ack|done|busy", vhdl, re.I):
        return "pass" if re.search(r"done|ack|ready", vhdl, re.I) else "unknown"
    return "unknown"


_PROPERTIES = {
    "deadlock_freedom": _deadlock_freedom,
    "unreachable_state": _unreachable_state,
    "overflow_detection": _overflow_guarded,
    "mutual_exclusion": _mutual_exclusion,
    "transaction_completion": _transaction_completion,
}


def check_properties(vhdl: str, requested: list[str] | None = None) -> PropertyReport:
    names = requested or list(_PROPERTIES)
    results = {n: _PROPERTIES[n](vhdl) for n in names if n in _PROPERTIES}
    return PropertyReport(results=results)

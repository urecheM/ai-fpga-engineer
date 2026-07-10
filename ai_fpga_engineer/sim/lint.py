"""Structural VHDL lint.

Fast, text-level checks that gate generated RTL before any expensive stage.
``fixable=True`` marks defect classes the debug agent knows how to repair
mechanically (missing library/use clauses); everything else is reported for
the HDL critic / a human. This is a *linter*, not a compiler — GHDL remains
the authority, and the lint gate exists only to fail fast and to give the
repair loop something well-defined to act on.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Issue:
    code: str
    message: str
    fixable: bool = False

    def __repr__(self) -> str:  # keeps assertion messages readable
        return f"{self.code}({'fixable' if self.fixable else 'manual'})"


_NUMERIC_TOKENS = re.compile(r"\b(unsigned|signed|to_unsigned|to_signed|resize)\b", re.I)


def lint(vhdl: str) -> list[Issue]:
    out: list[Issue] = []
    low = vhdl.lower()

    if not re.search(r"use\s+ieee\.std_logic_1164\.all\s*;", low):
        out.append(Issue("MISSING_STD_LOGIC",
                         "std_logic used without 'use ieee.std_logic_1164.all;'",
                         fixable=True))
    if _NUMERIC_TOKENS.search(vhdl) and not re.search(
            r"use\s+ieee\.numeric_std\.all\s*;", low):
        out.append(Issue("MISSING_NUMERIC_STD",
                         "numeric_std types used without 'use ieee.numeric_std.all;'",
                         fixable=True))

    ent = re.search(r"\bentity\s+(\w+)\s+is\b", low)
    arch = re.search(r"\barchitecture\s+\w+\s+of\s+(\w+)\s+is\b", low)
    if not ent:
        out.append(Issue("NO_ENTITY", "no entity declaration found"))
    if not arch:
        out.append(Issue("NO_ARCH", "no architecture body found"))
    if ent and arch and ent.group(1) != arch.group(1):
        out.append(Issue("ARCH_ENTITY_MISMATCH",
                         f"architecture targets '{arch.group(1)}' but entity is "
                         f"'{ent.group(1)}'"))

    # undriven outputs: every 'out' port must appear on the left of an assignment
    if ent:
        port_block = re.search(r"\bport\s*\((.*?)\)\s*;", vhdl, re.I | re.S)
        if port_block:
            body = vhdl[vhdl.lower().find("architecture"):] if arch else vhdl
            for m in re.finditer(r"(\w+)\s*:\s*out\b", port_block.group(1), re.I):
                port = m.group(1)
                if not re.search(rf"\b{re.escape(port)}\b\s*<=", body):
                    out.append(Issue("UNDRIVEN_OUTPUT",
                                     f"output port '{port}' is never assigned"))

    if vhdl.count("(") != vhdl.count(")"):
        out.append(Issue("PAREN_IMBALANCE",
                         f"unbalanced parentheses ({vhdl.count('(')} open, "
                         f"{vhdl.count(')')} close)"))
    return out

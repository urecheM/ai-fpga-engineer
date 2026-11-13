"""Parse the port clause of a VHDL entity into (name, direction, width) tuples.

Used for three things: checking a candidate's interface against the reference,
generating golden-vector testbenches, and generating the equivalence miter.
Handles the subset the v1 suite uses (std_logic, std_logic_vector, signed,
unsigned, with literal ``N downto M`` / ``M to N`` bounds). A width that depends
on a generic is reported as ``None`` rather than guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_COMMENT_RE = re.compile(r"--[^\n]*")
_ENTITY_RE = re.compile(r"\bentity\s+(\w+)\s+is\b", re.IGNORECASE)
_RANGE_RE = re.compile(r"\(\s*(\d+)\s+(downto|to)\s+(\d+)\s*\)", re.IGNORECASE)


@dataclass(frozen=True)
class PortSig:
    name: str
    direction: str  # in | out | inout | buffer
    width: int | None  # None if not a literal range
    type_name: str  # std_logic | std_logic_vector | unsigned | signed | ...
    is_vector: bool


def _port_clause(text: str, start: int) -> str | None:
    """Return the text inside ``port ( ... )`` after ``start``, parens balanced."""
    m = re.compile(r"\bport\s*\(", re.IGNORECASE).search(text, start)
    if not m:
        return None
    depth, i = 1, m.end()
    while i < len(text) and depth:
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
        i += 1
    return text[m.end() : i - 1] if depth == 0 else None


def _split_top(s: str) -> list[str]:
    """Split on ';' that are not inside parentheses."""
    out: list[str] = []
    cur: list[str] = []
    depth = 0
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == ";" and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return [x.strip() for x in out if x.strip()]


def parse_ports(vhdl: str, entity: str | None = None) -> list[PortSig] | None:
    """Ports of ``entity`` (or the first entity) in declaration order, or None."""
    text = _COMMENT_RE.sub("", vhdl or "")
    for m in _ENTITY_RE.finditer(text):
        if entity and m.group(1).lower() != entity.lower():
            continue
        clause = _port_clause(text, m.end())
        if clause is None:
            return None
        ports: list[PortSig] = []
        for decl in _split_top(clause):
            if ":" not in decl:
                return None
            names, rhs = decl.split(":", 1)
            rhs = rhs.split(":=")[0].strip()  # drop default values
            dm = re.match(r"(in|out|inout|buffer)\b\s*(.*)", rhs, re.IGNORECASE | re.S)
            if not dm:
                return None
            direction, typ = dm.group(1).lower(), dm.group(2).strip()
            type_name = re.match(r"[\w.]+", typ)
            tname = type_name.group(0).lower().split(".")[-1] if type_name else typ
            rm = _RANGE_RE.search(typ)
            if rm:
                a, b = int(rm.group(1)), int(rm.group(3))
                width: int | None = abs(a - b) + 1
                is_vec = True
            elif "(" in typ:
                width, is_vec = None, True  # generic-dependent range
            else:
                width, is_vec = 1, False
            for n in names.split(","):
                ports.append(PortSig(n.strip().lower(), direction, width, tname, is_vec))
        return ports
    return None


def entity_declaration(vhdl: str, entity: str | None = None) -> str:
    """The literal ``entity X is ... end ...;`` block (for the prompt), or ''."""
    m = re.search(
        r"\bentity\s+(\w+)\s+is\b.*?\bend\b(?:\s+entity)?(?:\s+\w+)?\s*;",
        vhdl or "",
        re.IGNORECASE | re.S,
    )
    if not m or (entity and m.group(1).lower() != entity.lower()):
        return ""
    return m.group(0)


def compare_interfaces(expected: list[PortSig], actual: list[PortSig] | None) -> list[str]:
    """Human-readable list of mismatches; empty list means the interface matches."""
    if actual is None:
        return ["could not parse the candidate's port clause"]
    problems: list[str] = []
    exp = {p.name: p for p in expected}
    act = {p.name: p for p in actual}
    for name in exp.keys() - act.keys():
        problems.append(f"missing port {name}")
    for name in act.keys() - exp.keys():
        problems.append(f"unexpected port {name}")
    for name in exp.keys() & act.keys():
        e, a = exp[name], act[name]
        if e.direction != a.direction:
            problems.append(f"{name}: direction {a.direction}, expected {e.direction}")
        if e.width is not None and a.width is not None and e.width != a.width:
            problems.append(f"{name}: width {a.width}, expected {e.width}")
        if e.is_vector != a.is_vector:
            problems.append(f"{name}: scalar/vector mismatch")
    return sorted(problems)

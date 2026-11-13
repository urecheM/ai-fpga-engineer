"""Faults:
* syntactic: the result does not compile, so the compiler alone catches them.
* semantic: result still compiles and synthesises, but behaves
  differently
"""

from __future__ import annotations

import random
import re
from collections.abc import Callable

from ..parsing.ports import parse_ports

Operator = Callable[[str, random.Random], str | None]

_I = re.IGNORECASE


def _pick(matches: list[re.Match[str]], rng: random.Random) -> re.Match[str] | None:
    return matches[rng.randrange(len(matches))] if matches else None


def _splice(text: str, m: re.Match[str], new: str, group: int = 0) -> str:
    return text[: m.start(group)] + new + text[m.end(group) :]


def _code_only(text: str) -> str:
    """Blank out comments (same length) so regex offsets still line up."""
    return re.sub(r"--[^\n]*", lambda m: " " * len(m.group(0)), text)


# syntactic
def drop_semicolon(text: str, rng: random.Random) -> str | None:
    return text.replace(";", "", 1) if ";" in text else None


def comment_out_signal(text: str, rng: random.Random) -> str | None:
    new = re.sub(r"\bsignal\b", "-- signal", text, count=1)
    return new if new != text else None


def truncate(text: str, rng: random.Random) -> str | None:
    lines = text.splitlines()
    return "\n".join(lines[: max(3, len(lines) // 2)]) if len(lines) > 6 else None


# semantic
def invert_condition(text: str, rng: random.Random) -> str | None:
    """``if C then`` -> ``if not (C) then``, skipping clock-edge conditions."""
    code = _code_only(text)
    ms = [
        m
        for m in re.finditer(r"\b(?:els)?if\s+(.+?)\s+then\b", code, _I | re.S)
        if "edge" not in m.group(1).lower()
    ]
    m = _pick(ms, rng)
    return _splice(text, m, f"not ({m.group(1)})", 1) if m else None


def off_by_one(text: str, rng: random.Random) -> str | None:
    """Shift an integer literal in a comparison: ``cnt = 7`` -> ``cnt = 6``."""
    code = _code_only(text)
    ms = list(re.finditer(r"(?<![<>/=])(=|/=|<|>|<=|>=)\s*(\d+)\b(?!\s*(?:ns|ps|downto|to))", code))
    m = _pick(ms, rng)
    if not m:
        return None
    v = int(m.group(2))
    nv = v - 1 if v > 0 and rng.random() < 0.5 else v + 1
    return _splice(text, m, str(nv), 2)


_SWAPS = [
    (r"\+", "-"),
    (r"(?<![<=>/])-(?!-)", "+"),
    (r"\band\b", "or"),
    (r"\bor\b", "and"),
    (r"\bxor\b", "or"),
]


def swap_operator(text: str, rng: random.Random) -> str | None:
    """Swap one arithmetic/logic operator (+/-, and/or, xor->or)."""
    code = _code_only(text)
    cands: list[tuple[re.Match[str], str]] = []
    for pat, repl in _SWAPS:
        for m in re.finditer(pat, code, _I):
            tail = code[m.end() : m.end() + 12].lower()
            if "downto" in tail or " to " in tail:
                continue
            cands.append((m, repl))
    if not cands:
        return None
    m, repl = cands[rng.randrange(len(cands))]
    return _splice(text, m, repl)


def flip_reset_polarity(text: str, rng: random.Random) -> str | None:
    """Active-high reset treated as active-low (and vice versa)."""
    code = _code_only(text)
    m = re.search(r"\b(rst|reset)(_n)?\s*=\s*'([01])'", code, _I)
    if not m:
        return None
    flipped = "0" if m.group(3) == "1" else "1"
    return text[: m.start(3)] + flipped + text[m.end(3) :]


def drop_case_branch(text: str, rng: random.Random) -> str | None:
    """Replace the body of one non-``others`` case branch with ``null;``."""
    code = _code_only(text)
    heads = [
        m
        for m in re.finditer(r"\bwhen\s+([^;=]+?)\s*=>", code, _I)
        if "others" not in m.group(1).lower()
    ]
    m = _pick(heads, rng)
    if not m:
        return None
    nxt = re.compile(r"\bwhen\s+[^;=]+?=>|\bend\s+case\b", _I).search(code, m.end())
    if not nxt:
        return None
    body = text[m.end() : nxt.start()]
    if not body.strip() or body.strip().lower() == "null;":
        return None
    return text[: m.end()] + " null;\n" + text[nxt.start() :]


def stuck_at_bit(text: str, rng: random.Random) -> str | None:
    """Tie one bit of one output port to '0' via a shadow signal."""
    ports = parse_ports(text)
    if not ports:
        return None
    outs = [p for p in ports if p.direction == "out" and p.width]
    if not outs:
        return None
    p = outs[rng.randrange(len(outs))]
    arch = re.search(r"\barchitecture\s+\w+\s+of\s+\w+\s+is\b", text, _I)
    begin = re.search(r"\bbegin\b", text[arch.end() :], _I) if arch else None
    if not arch or not begin:
        return None
    shadow = f"{p.name}_mut"
    body_start = arch.end() + begin.end()
    head, body = text[:body_start], text[body_start:]
    new_body, n = re.subn(rf"\b{re.escape(p.name)}(\s*<=)", rf"{shadow}\1", body, flags=_I)
    if not n:
        return None
    if p.is_vector:
        w, k = p.width or 1, rng.randrange(p.width or 1)
        hi = f"{shadow}({w - 1} downto {k + 1}) & " if k < w - 1 else ""
        lo = f" & {shadow}({k - 1} downto 0)" if k > 0 else ""
        decl = f"std_logic_vector({w - 1} downto 0)"
        drive = f"{p.name} <= {hi}'0'{lo};" if w > 1 else f'{p.name} <= "0";'
    else:
        decl, drive = "std_logic", f"{p.name} <= '0';"
    sig = f"\n  signal {shadow} : {decl};"
    head = head[: arch.end()] + sig + head[arch.end() :]
    return head + f"\n  {drive}" + new_body


def wrong_clock_edge(text: str, rng: random.Random) -> str | None:
    new = re.sub(r"rising_edge\s*\(", "falling_edge(", text, count=1, flags=_I)
    return new if new != text else None


SYNTACTIC: dict[str, Operator] = {
    "drop_semicolon": drop_semicolon,
    "undeclared": comment_out_signal,
    "truncate": truncate,
}

SEMANTIC: dict[str, Operator] = {
    "invert_condition": invert_condition,
    "off_by_one": off_by_one,
    "swap_operator": swap_operator,
    "stuck_at_bit": stuck_at_bit,
    "flip_reset_polarity": flip_reset_polarity,
    "drop_case_branch": drop_case_branch,
    "wrong_clock_edge": wrong_clock_edge,
}


def apply_fault(text: str, mode: str, rng: random.Random) -> tuple[str, str]:
    if mode == "syntactic":
        pool = dict(SYNTACTIC)
    elif mode == "semantic":
        pool = dict(SEMANTIC)
    elif mode == "mixed":
        pool = {**SYNTACTIC, **SEMANTIC}
    else:
        raise ValueError(f"unknown fault mode {mode!r}")
    names = sorted(pool)
    rng.shuffle(names)
    for name in names:
        out = pool[name](text, rng)
        if out is not None and out != text:
            return out, name
    return text, "none_applicable"

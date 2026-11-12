#`cli mutation-campaign` applies every operator and reports which stage detected each one including escapes.
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable


def _sub1(pattern: str, repl: str, text: str, flags: int = 0) -> str | None:
    new, n = re.subn(pattern, repl, text, count=1, flags=flags)
    return new if n else None


def drop_numeric_std(text: str) -> str | None:
    return _sub1(r"^\s*use\s+ieee\.numeric_std\.all\s*;\s*\n", "", text,
                 re.IGNORECASE | re.MULTILINE)


def remove_when_others(text: str) -> str | None:
    return _sub1(r"^\s*when\s+others\s*=>\s*res_i\s*<=\s*\(others\s*=>\s*'0'\);\s*\n",
                 "", text, re.IGNORECASE | re.MULTILINE)


def swap_add_to_sub(text: str) -> str | None:
    return _sub1(r"resize\(unsigned\(a\),\s*WIDTH\+1\)\s*\+\s*resize\(unsigned\(b\),\s*WIDTH\+1\)",
                 "resize(unsigned(a), WIDTH+1) - resize(unsigned(b), WIDTH+1)", text)


def stuck_carry_zero(text: str) -> str | None:
    return _sub1(r"carry\s*<=\s*res_i\(WIDTH\);", "carry  <= '0';", text)


def invert_zero_compare(text: str) -> str | None:
    return _sub1(r"=\s*std_logic_vector\(to_unsigned\(0,\s*WIDTH\)\)",
                 "/= std_logic_vector(to_unsigned(0, WIDTH))", text)


def wrong_clock_edge(text: str) -> str | None:
    return _sub1(r"rising_edge\(clk\)", "falling_edge(clk)", text)


def invert_reset_polarity(text: str) -> str | None:
    return _sub1(r"if\s+rst\s*=\s*'1'\s+then", "if rst = '0' then", text)


def stuck_terminal_count(text: str) -> str | None:
    return _sub1(r"tc\s*<=\s*'1'\s+when\s+cnt\s*=\s*\(cnt'range\s*=>\s*'1'\)\s+else\s+'0';",
                 "tc    <= '0';", text)


@dataclass(frozen=True)
class Mutation:
    name: str
    fn: Callable[[str], str | None]
    expected_detector: str
    note: str


MUTATIONS: list[Mutation] = [
    Mutation("drop_numeric_std", drop_numeric_std, "lint-gate",
             "missing use clause; lint-fixable, exercises the repair loop"),
    Mutation("remove_when_others", remove_when_others, "hdl-critic",
             "case without default -> inferred latch; blocking, not auto-fixable"),
    Mutation("swap_add_to_sub", swap_add_to_sub, "ghdl-simulation",
             "ADD computes a-b; invisible to model-level checks"),
    Mutation("stuck_carry_zero", stuck_carry_zero, "ghdl-simulation",
             "carry tied low; invisible to model-level checks"),
    Mutation("invert_zero_compare", invert_zero_compare, "ghdl-simulation",
             "zero flag inverted; invisible to model-level checks"),
    Mutation("wrong_clock_edge", wrong_clock_edge, "ghdl-simulation",
             "falling-edge clocking against a rising-edge testbench"),
    Mutation("invert_reset_polarity", invert_reset_polarity, "ghdl-simulation",
             "reset never fires / fires constantly"),
    Mutation("stuck_terminal_count", stuck_terminal_count, "ghdl-simulation",
             "tc never asserts; invisible to model-level checks"),
]


def names() -> list[str]:
    return [m.name for m in MUTATIONS]


def get(name: str) -> Mutation:
    for m in MUTATIONS:
        if m.name == name:
            return m
    raise KeyError(f"unknown mutation {name!r}; known: {', '.join(names())}")


def apply(name: str, vhdl: str) -> str | None:
    return get(name).fn(vhdl)

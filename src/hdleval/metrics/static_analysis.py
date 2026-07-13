"""Static (tool-free) analysis of VHDL source.

These metrics quantify design *structure* independently of any simulator or
synthesizer: hierarchy, combinational complexity, inferred latches, reset
strategy, FSM complexity, module decomposition and fan-out. They are heuristic
but deterministic and are useful comparative signals across models.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

_KEYWORDS = {
    "process": re.compile(r"\bprocess\b", re.I),
    "if": re.compile(r"\bif\b", re.I),
    "case": re.compile(r"\bcase\b", re.I),
    "when": re.compile(r"\bwhen\b", re.I),
    "entity": re.compile(r"\bentity\s+\w+\s+is", re.I),
    "component": re.compile(r"\bcomponent\s+\w+", re.I),
    "instantiation": re.compile(r"\b\w+\s*:\s*entity\b", re.I),
    "signal": re.compile(r"\bsignal\b", re.I),
    "assign": re.compile(r"<=", re.I),
}


@dataclass(frozen=True)
class StaticMetrics:
    lines: int
    processes: int
    hierarchy_depth: int
    combinational_complexity: int
    inferred_latch_risk: int
    has_reset: bool
    reset_style: str  # none | async | sync
    fsm_states: int
    modules: int
    max_fan_out: int
    modularity: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _count(rx: re.Pattern[str], text: str) -> int:
    return len(rx.findall(text))


def analyze_vhdl(vhdl: str) -> StaticMetrics:
    text = vhdl or ""
    lines = text.count("\n") + 1 if text else 0
    processes = _count(_KEYWORDS["process"], text) // 2  # process ... end process
    ifs = _count(_KEYWORDS["if"], text)
    cases = _count(_KEYWORDS["case"], text)
    whens = _count(_KEYWORDS["when"], text)
    comb = ifs + cases + whens

    reset_style = "none"
    if re.search(r"rising_edge|falling_edge", text, re.I) and re.search(
        r"if\s+\w*rst\w*\s*=\s*'1'.*?then", text, re.I | re.S
    ):
        reset_style = "sync"
    if re.search(r"if\s+\w*rst\w*\s*=\s*'1'\s*then", text, re.I) and re.search(
        r"process\s*\([^)]*\brst\w*\b", text, re.I
    ):
        reset_style = "async"
    has_reset = reset_style != "none"

    # crude latch risk: combinational process with if but no else / default
    latch_risk = 0
    for block in re.findall(r"process\b.*?end\s+process", text, re.I | re.S):
        if (
            "rising_edge" not in block.lower()
            and "if" in block.lower()
            and "else" not in block.lower()
        ):
            latch_risk += 1

    # FSM state count: entries in a state type enum
    fsm_states = 0
    m = re.search(r"type\s+\w*state\w*\s+is\s*\((.*?)\)", text, re.I | re.S)
    if m:
        fsm_states = len([s for s in m.group(1).split(",") if s.strip()])

    modules = max(1, _count(_KEYWORDS["entity"], text))
    instantiations = _count(_KEYWORDS["instantiation"], text)
    hierarchy_depth = 1 + (1 if instantiations else 0)

    # fan-out: max number of reads of any signal name
    signals = re.findall(r"signal\s+(\w+)", text, re.I)
    max_fan_out = 0
    for s in set(signals):
        max_fan_out = max(max_fan_out, len(re.findall(rf"\b{re.escape(s)}\b", text)) - 1)

    modularity = round(min(1.0, (modules + instantiations) / (1 + processes + comb / 8)), 3)

    return StaticMetrics(
        lines=lines,
        processes=processes,
        hierarchy_depth=hierarchy_depth,
        combinational_complexity=comb,
        inferred_latch_risk=latch_risk,
        has_reset=has_reset,
        reset_style=reset_style,
        fsm_states=fsm_states,
        modules=modules,
        max_fan_out=max_fan_out,
        modularity=modularity,
    )

"""Requirements agent: natural-language request -> machine-readable Specification.

Deliberately rule-based and transparent: keyword classification into the four
supported design classes, width extraction, and case-sensitive operation-token
scanning (so prose 'and'/'or' never become ALU ops). Anything unrecognised is
classified 'unknown' and reported — never guessed at.
"""
from __future__ import annotations

import math
import re

from .base import Agent
from ..core.spec import Specification, Port, Operation
from ..reference.models import ALU_OP_NAMES

_CLASS_KEYWORDS = [
    ("alu", ("alu", "arithmetic logic unit")),
    ("comparator", ("comparator", "compare unit", "magnitude compare")),
    ("counter", ("counter",)),
    ("register", ("register", "flip-flop bank", "d-ff")),
]

_TITLES = {
    "alu": "{w}-bit ALU",
    "comparator": "{w}-bit Unsigned Comparator",
    "counter": "{w}-bit Synchronous Up-Counter",
    "register": "{w}-bit Register with Load Enable",
    "unknown": "Unclassified Design Request",
}


class RequirementsAgent(Agent):
    name = "requirements"

    def run(self, project) -> Specification:
        request = getattr(project, "request", "") or ""
        low = request.lower()

        design_class = "unknown"
        for cls, keys in _CLASS_KEYWORDS:
            if any(k in low for k in keys):
                design_class = cls
                break

        m = re.search(r"(\d+)\s*[- ]?\s*bit", low)
        width = max(1, min(64, int(m.group(1)))) if m else 8

        # case-sensitive scan: 'ADD'/'SUB' are ops, prose 'and'/'or' are not
        ops: list[Operation] = []
        if design_class == "alu":
            seen = []
            for tok in re.findall(r"\b[A-Z]{2,4}\b", request):
                if tok in ALU_OP_NAMES and tok not in seen:
                    seen.append(tok)
            if not seen:
                seen = ["ADD", "SUB", "AND", "OR", "XOR"]
            ops = [Operation(o) for o in seen]

        spec = Specification(
            name=f"{design_class}{width}" if design_class != "unknown" else f"design{width}",
            title=_TITLES[design_class].format(w=width),
            design_class=design_class,
            data_width=width,
            clocking=("combinational" if design_class in ("alu", "comparator")
                      else "synchronous, rising edge"),
            operations=ops,
            ports=self._ports(design_class, width, len(ops)),
            assumptions=self._assumptions(design_class),
            source_request=request,
        )
        self.log(project, f"classified as '{spec.design_class}', width {width}"
                 + (f", ops {', '.join(o.name for o in ops)}" if ops else ""),
                 "success" if design_class != "unknown" else "warn")
        return spec

    @staticmethod
    def _ports(cls: str, w: int, n_ops: int) -> list[Port]:
        if cls == "alu":
            opw = max(1, math.ceil(math.log2(max(2, n_ops or 5))))
            return [Port("a", "in", w, "data"), Port("b", "in", w, "data"),
                    Port("op", "in", opw, "opcode"),
                    Port("result", "out", w, "data"),
                    Port("carry", "out", 1, "flag"), Port("zero", "out", 1, "flag")]
        if cls == "comparator":
            return [Port("a", "in", w, "data"), Port("b", "in", w, "data"),
                    Port("gt", "out", 1, "flag"), Port("eq", "out", 1, "flag"),
                    Port("lt", "out", 1, "flag")]
        if cls == "counter":
            return [Port("clk", "in", 1, "clock"), Port("rst", "in", 1, "reset"),
                    Port("en", "in", 1, "enable"),
                    Port("count", "out", w, "data"), Port("tc", "out", 1, "flag")]
        if cls == "register":
            return [Port("clk", "in", 1, "clock"), Port("rst", "in", 1, "reset"),
                    Port("en", "in", 1, "enable"), Port("d", "in", w, "data"),
                    Port("q", "out", w, "data")]
        return []

    @staticmethod
    def _assumptions(cls: str) -> list[str]:
        common = ["Unsigned interpretation of all data buses."]
        if cls in ("counter", "register"):
            return common + ["Synchronous active-high reset; single clock domain.",
                             "Enable is sampled on the rising edge."]
        if cls in ("alu", "comparator"):
            return common + ["Purely combinational unless the chosen architecture "
                             "registers the outputs (then latency = 1 clock)."]
        return common

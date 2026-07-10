"""Architecture critic: reviews design *intent* before anything is generated.

Rule-based checks on the specification/architecture pair. 'block' findings
send the architecture back for revision (bounded loop in the orchestrator);
the RTL-level critic (hdl_critic_agent) reviews the *generated code* later.
"""
from __future__ import annotations

from dataclasses import dataclass

from .base import Agent
from ..core.spec import Specification
from .architecture_agent import Architecture


@dataclass
class Finding:
    severity: str        # block | warn | info
    rule: str
    message: str


class CriticAgent(Agent):
    name = "design-critic"

    def run(self, project, spec: Specification, arch: Architecture) -> list[Finding]:
        findings: list[Finding] = []
        if spec.design_class == "unknown":
            findings.append(Finding("block", "UNSUPPORTED_CLASS",
                                    "request did not map to a supported design "
                                    "class; refusing to generate a guess."))
        if spec.data_width > 32:
            findings.append(Finding("warn", "WIDE_DATAPATH",
                                    f"{spec.data_width}-bit datapath: exhaustive "
                                    "checking is infeasible; bounded checks only."))
        if spec.design_class in ("counter", "register") and \
                not any(p.role == "reset" for p in spec.ports):
            findings.append(Finding("block", "NO_RESET_PLANNED",
                                    "stateful design planned without a reset."))
        for f in findings:
            self.log(project, f"{f.rule}: {f.message}",
                     "error" if f.severity == "block" else "warn")
        if not findings:
            self.log(project, "no findings; architecture accepted", "success")
        return findings

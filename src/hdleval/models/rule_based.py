"""Rule-based provider backed by the ``ai_fpga_engineer`` pipeline.

This adapter lets the mature, deterministic rule-based VHDL pipeline (the
``ai_fpga_engineer`` package that this repository grew from) be evaluated as a
*model* through the identical hdleval harness. It classifies the benchmark's
natural-language specification and, for the four design classes the pipeline
supports (ALU, counter, register, comparator), emits synthesizable VHDL via the
template generators. For specifications outside that scope it returns no code —
which the harness records as ``no_code_generated``.

The scientific value: this is a strong, verified-by-construction baseline on its
supported classes and an honest zero elsewhere, so a leaderboard that includes it
exposes exactly the coverage/quality trade-off between a narrow rule-based system
and broader LLM generation. Fully deterministic; no network, no API key.
"""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

from ..config.schema import ModelConfig
from .base import ModelProvider, ModelRequest, ModelResponse


def _ensure_importable() -> None:
    # ai_fpga_engineer lives at the repository root, alongside src/.
    repo_root = Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


class RuleBasedProvider(ModelProvider):
    name = "rule_based"

    def __init__(self) -> None:
        self.available = True
        try:
            _ensure_importable()
            import ai_fpga_engineer  # noqa: F401

            self.available = True
        except Exception:
            self.available = False

    def generate(self, request: ModelRequest) -> ModelResponse:
        t0 = time.perf_counter()
        spec_text = request.context.get("specification", "") or request.prompt
        text, finish = self._generate_vhdl(spec_text)
        latency = round(time.perf_counter() - t0, 4)
        ptok = max(1, len(request.system + request.prompt) // 4)
        ctok = max(1, len(text) // 4)
        return ModelResponse(
            text=text,
            provider=self.name,
            model_id=request.config.model_id or "ai_fpga_engineer-rule-based",
            prompt_tokens=ptok,
            completion_tokens=ctok,
            latency_s=latency,
            finish_reason=finish,
            raw={"deterministic": True, "engine": "ai_fpga_engineer"},
        )

    def _generate_vhdl(self, specification: str) -> tuple[str, str]:
        if not self.available:
            return (
                "The ai_fpga_engineer pipeline is not importable in this environment."
            ), "unavailable"
        _ensure_importable()
        import tempfile

        from ai_fpga_engineer.agents.hdl_agent import HDLAgent
        from ai_fpga_engineer.agents.requirements_agent import RequirementsAgent
        from ai_fpga_engineer.core.project import Project

        h = hashlib.sha256(specification.encode()).hexdigest()[:8]
        proj = Project(
            f"hdleval_{h}", Path(tempfile.mkdtemp()) / "p", request=specification, quiet=True
        ).init()
        spec = RequirementsAgent().run(proj)
        if spec.design_class == "unknown":
            return (
                "This specification is outside the rule-based pipeline's four "
                "supported design classes (alu, counter, register, comparator); "
                "no VHDL was generated."
            ), "unsupported_class"
        design = HDLAgent().run(proj, spec)
        return f"```vhdl\n{design.vhdl.strip()}\n```", "stop"


def rule_based_factory(_: ModelConfig) -> ModelProvider:
    return RuleBasedProvider()

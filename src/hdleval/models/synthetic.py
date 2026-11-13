from __future__ import annotations

import hashlib
import random

from ..config.schema import ModelConfig
from .base import ModelProvider, ModelRequest, ModelResponse
from .faults import apply_fault


def _det_unit(*parts: str) -> float:
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return (int(h[:8], 16) % 10_000) / 10_000.0


class SyntheticProvider(ModelProvider):
    name = "synthetic"

    def __init__(self, fidelity: float = 0.8, seed: int = 0, fault_mode: str = "syntactic") -> None:
        self.fidelity = fidelity
        self.seed = seed
        self.fault_mode = fault_mode
        self.available = True

    def generate(self, request: ModelRequest) -> ModelResponse:
        ref = request.context.get("reference_hdl", "")
        entity = request.context.get("entity", "design")
        difficulty = float(request.context.get("difficulty", 40)) / 100.0
        key = f"{entity}:{self.seed}:{request.config.name}:{request.run_seed}"
        roll = _det_unit(key)
        p_success = max(0.02, min(0.99, self.fidelity - 0.5 * difficulty))

        finish = "stop"
        fault = "none"
        if not ref:
            text = "I could not produce a design for this specification."
            finish = "no_reference"
        elif roll <= p_success:
            text = f"```vhdl\n{ref.strip()}\n```"
        else:
            if _det_unit(key, "empty") < 0.2:
                text = "Here is a description but no complete VHDL was produced."
                finish = "incomplete"
                fault = "no_code"
            else:
                rng = random.Random(int(_det_unit(key, "fault") * 10_000_000))
                broken, fault = apply_fault(ref, self.fault_mode, rng)
                text = f"```vhdl\n{broken.strip()}\n```"

        latency = round(0.4 + difficulty * 2.0 + _det_unit(key, "lat"), 3)
        ptok = max(1, len(request.system + request.prompt) // 4)
        ctok = max(1, len(text) // 4)
        return ModelResponse(
            text=text,
            provider=self.name,
            model_id=request.config.model_id or f"synthetic-f{self.fidelity}",
            prompt_tokens=ptok,
            completion_tokens=ctok,
            latency_s=latency,
            finish_reason=finish,
            raw={
                "synthetic": True,
                "fidelity": self.fidelity,
                "fault_mode": self.fault_mode,
                "fault": fault,
            },
        )


def synthetic_factory(cfg: ModelConfig) -> ModelProvider:
    fidelity = float(cfg.extra.get("fidelity", 0.8))
    seed = int(cfg.seed or 0)
    mode = str(cfg.extra.get("fault_mode", "syntactic"))
    return SyntheticProvider(fidelity=fidelity, seed=seed, fault_mode=mode)

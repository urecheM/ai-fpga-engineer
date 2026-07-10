"""Deterministic *synthetic* baseline provider (a negative/positive control).

This provider models an imperfect language model by degrading the benchmark's
reference implementation as a deterministic function of (benchmark difficulty,
per-model ``fidelity``, seed). It never calls the network, so it makes the
whole pipeline — metrics, failure classification, leaderboard, statistics —
exercisable and reproducible *before* a real model API key is configured.

It is clearly labelled as synthetic in every artifact. Swap in
``provider: anthropic`` to evaluate a real model through the identical harness.
"""
from __future__ import annotations

import hashlib
import re

from ..config.schema import ModelConfig
from .base import ModelProvider, ModelRequest, ModelResponse


def _det_unit(*parts: str) -> float:
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return (int(h[:8], 16) % 10_000) / 10_000.0


def _corrupt(vhdl: str, kind: str) -> str:
    if kind == "drop_semicolon":
        return vhdl.replace(";", "", 1)
    if kind == "undeclared":
        return re.sub(r"\bsignal\b", "-- signal", vhdl, count=1)
    if kind == "truncate":
        lines = vhdl.splitlines()
        return "\n".join(lines[: max(3, len(lines) // 2)])
    return vhdl


class SyntheticProvider(ModelProvider):
    name = "synthetic"

    def __init__(self, fidelity: float = 0.8, seed: int = 0) -> None:
        self.fidelity = fidelity
        self.seed = seed
        self.available = True

    def generate(self, request: ModelRequest) -> ModelResponse:
        ref = request.context.get("reference_hdl", "")
        entity = request.context.get("entity", "design")
        difficulty = float(request.context.get("difficulty", 40)) / 100.0
        key = f"{entity}:{self.seed}:{request.config.name}"
        roll = _det_unit(key)
        # success probability falls with difficulty, rises with fidelity
        p_success = max(0.02, min(0.99, self.fidelity - 0.5 * difficulty))

        finish = "stop"
        if not ref:
            text = "I could not produce a design for this specification."
            finish = "no_reference"
        elif roll <= p_success:
            text = f"```vhdl\n{ref.strip()}\n```"
        else:
            # produce a plausible-but-broken variant
            kinds = ["drop_semicolon", "undeclared", "truncate"]
            kind = kinds[int(_det_unit(key, "kind") * len(kinds)) % len(kinds)]
            if _det_unit(key, "empty") < 0.2:
                text = "Here is a description but no complete VHDL was produced."
                finish = "incomplete"
            else:
                text = f"```vhdl\n{_corrupt(ref, kind).strip()}\n```"

        latency = round(0.4 + difficulty * 2.0 + _det_unit(key, "lat"), 3)
        ptok = max(1, len(request.system + request.prompt) // 4)
        ctok = max(1, len(text) // 4)
        return ModelResponse(
            text=text, provider=self.name,
            model_id=request.config.model_id or f"synthetic-f{self.fidelity}",
            prompt_tokens=ptok, completion_tokens=ctok, latency_s=latency,
            finish_reason=finish, raw={"synthetic": True, "fidelity": self.fidelity},
        )


def synthetic_factory(cfg: ModelConfig) -> ModelProvider:
    fidelity = float(cfg.extra.get("fidelity", 0.8))
    seed = int(cfg.seed or 0)
    return SyntheticProvider(fidelity=fidelity, seed=seed)

from __future__ import annotations

import hashlib
import time

from .base import ModelProvider, ModelRequest, ModelResponse


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class ReferenceProvider(ModelProvider):
    name = "reference"
    available = True

    def generate(self, request: ModelRequest) -> ModelResponse:
        t0 = time.perf_counter()
        ref = request.context.get("reference_hdl", "")
        entity = request.context.get("entity", "design")
        if ref:
            text = (
                f"Here is a synthesizable VHDL implementation of `{entity}`.\n\n"
                f"```vhdl\n{ref.strip()}\n```\n"
            )
            finish = "stop"
        else:
            text = "No reference implementation is available for this benchmark."
            finish = "no_reference"
        h = int(hashlib.sha256((request.prompt + entity).encode()).hexdigest(), 16)
        pseudo_latency = 0.05 + (h % 100) / 1000.0
        _ = time.perf_counter() - t0
        return ModelResponse(
            text=text,
            provider=self.name,
            model_id=request.config.model_id or "reference-golden",
            prompt_tokens=_approx_tokens(request.system + request.prompt),
            completion_tokens=_approx_tokens(text),
            latency_s=round(pseudo_latency, 4),
            finish_reason=finish,
            raw={"deterministic": True},
        )

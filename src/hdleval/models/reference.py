"""Deterministic reference provider.

This provider does not call any network service. It returns a benchmark's
verified reference implementation (supplied via ``request.context``) wrapped in
a Markdown code fence so the *entire* downstream pipeline — parsing, compilation,
synthesis, simulation, verification — is exercised deterministically and with
no API key. It represents an idealised "perfect model" baseline and is the
backbone of the reproducible smoke experiment.

When no reference HDL is available it emits an empty stub, which the harness
records as a generation failure — a useful negative control.
"""

from __future__ import annotations

import hashlib
import time

from .base import ModelProvider, ModelRequest, ModelResponse


def _approx_tokens(text: str) -> int:
    # A stable, network-free token estimate (~4 chars/token).
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
        # deterministic pseudo-latency derived from a content hash (repeatable)
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

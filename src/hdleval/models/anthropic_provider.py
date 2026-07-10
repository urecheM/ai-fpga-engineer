"""Real Anthropic Messages API provider.

Activated only when the ``anthropic`` SDK is importable and ``ANTHROPIC_API_KEY``
is set. Responses are cached to disk (keyed by a hash of the full request) so
that experiments remain reproducible despite non-deterministic sampling: a
re-run reads the cached completion instead of issuing a new billable call.
Set ``HDLEVAL_DISABLE_CACHE=1`` to force fresh calls.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from .base import ModelProvider, ModelRequest, ModelResponse

_CACHE_DIR = Path(os.environ.get("HDLEVAL_CACHE_DIR", ".hdleval_cache/responses"))


def _cache_key(request: ModelRequest) -> str:
    payload = json.dumps(
        {
            "system": request.system,
            "prompt": request.prompt,
            "model_id": request.config.model_id,
            "temperature": request.config.temperature,
            "top_p": request.config.top_p,
            "max_tokens": request.config.max_tokens,
            "seed": request.config.seed,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


class AnthropicProvider(ModelProvider):
    name = "anthropic"

    def __init__(self, model_id: str = "claude-sonnet-4-6") -> None:
        self.model_id = model_id
        self.available = False
        self._client = None
        key = os.environ.get("ANTHROPIC_API_KEY")
        if key:
            try:  # pragma: no cover - depends on optional dep + network
                import anthropic

                self._client = anthropic.Anthropic(api_key=key)
                self.available = True
            except Exception:
                self.available = False

    def _read_cache(self, key: str) -> ModelResponse | None:
        if os.environ.get("HDLEVAL_DISABLE_CACHE") == "1":
            return None
        f = _CACHE_DIR / f"{key}.json"
        if f.exists():
            d = json.loads(f.read_text())
            return ModelResponse(**d)
        return None

    def _write_cache(self, key: str, resp: ModelResponse) -> None:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (_CACHE_DIR / f"{key}.json").write_text(json.dumps(resp.__dict__))

    def generate(self, request: ModelRequest) -> ModelResponse:  # pragma: no cover
        key = _cache_key(request)
        cached = self._read_cache(key)
        if cached is not None:
            return cached
        if not self.available or self._client is None:
            # Degrade gracefully: the harness records this as a generation
            # failure (no_code_generated) rather than crashing the whole run.
            # The CLI preflight warns before the run so the cause is obvious.
            return ModelResponse(
                text="",
                provider=self.name,
                model_id=request.config.model_id or self.model_id,
                latency_s=0.0,
                finish_reason="unavailable",
                raw={"reason": "ANTHROPIC_API_KEY or anthropic SDK missing"},
            )
        cfg = request.config
        t0 = time.perf_counter()
        msg = self._client.messages.create(
            model=cfg.model_id or self.model_id,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
            top_p=cfg.top_p,
            system=request.system or cfg.system_prompt,
            messages=[{"role": "user", "content": request.prompt}],
        )
        latency = time.perf_counter() - t0
        text = "".join(block.text for block in msg.content if block.type == "text")
        resp = ModelResponse(
            text=text,
            provider=self.name,
            model_id=cfg.model_id or self.model_id,
            prompt_tokens=msg.usage.input_tokens,
            completion_tokens=msg.usage.output_tokens,
            latency_s=round(latency, 4),
            finish_reason=msg.stop_reason or "stop",
            raw={"id": msg.id},
        )
        self._write_cache(key, resp)
        return resp

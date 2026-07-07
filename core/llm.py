"""LLM provider abstraction.

Platform designed so that every agent that could benefit from a language
model goes thru this interface. By default runs fully offline with a
deterministic rule-based provider -> the pipeline works w/ no API key and no
network. !!!: Set ANTHROPIC_API_KEY (and have the `anthropic` SDK + network) to use
a real model instead (for open-ended requests etc. etc.) 
"""
from __future__ import annotations

import os
from typing import Protocol


class LLMProvider(Protocol):
    name = "offline/rule-based"
    def complete(self, prompt: str) -> str:  # pragma: no cover
        raise NotImplementedError(
            "No LLM configured. The pipeline is rule-based and does not need "
            "one; attach a provider here only for a specific, benchmarked "
            "experiment (see docs/CLAIMS.md).")
    def complete(self, system: str, prompt: str, max_tokens: int = 1024) -> str: ...


class OfflineProvider:
    """Deterministic, no-network fallback.

    No free-form text.
    Rule-based agents handle all supported design classes without it ->
    this only matters for genuinely open-ended requests.
    """
    name = "offline-rule-based"
    available = True

    def complete(self, system: str, prompt: str, max_tokens: int = 1024) -> str:
        return (
            "[offline provider] No language model is configured. The rule-based "
            "agents handle all supported design classes. To enable free-form "
            "reasoning, set ANTHROPIC_API_KEY."
        )


class AnthropicProvider:
    """Wrapper over the Anthropic Messages API. Activated only if the SDK,
    a key and network all present."""
    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-4-6"):
        self.model = model
        self.available = False
        self._client = None
        key = os.environ.get("ANTHROPIC_API_KEY")
        if key:
            try:
                import anthropic  # type: ignore
                self._client = anthropic.Anthropic(api_key=key)
                self.available = True
            except Exception:
                self.available = False

    def complete(self, system: str, prompt: str, max_tokens: int = 1024) -> str:
        if not self.available or self._client is None:
            raise RuntimeError("Anthropic provider unavailable")
        msg = self._client.messages.create(
            model=self.model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


def get_provider() -> LLMProvider:
    ap = AnthropicProvider()
    if ap.available:
        return ap
    return OfflineProvider()

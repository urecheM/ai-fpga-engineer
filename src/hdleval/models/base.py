"""Provider-neutral request/response types and the provider interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from ..config.schema import ModelConfig
from ..registry.pricing import compute_cost_usd


@dataclass(frozen=True)
class ModelRequest:
    """A single inference request."""

    system: str
    prompt: str
    config: ModelConfig
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    """The result of one inference call, with accounting for reproducibility."""

    text: str
    provider: str
    model_id: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_s: float = 0.0
    finish_reason: str = "stop"
    raw: dict[str, Any] = field(default_factory=dict)
    cost_usd: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


def estimate_cost(response: ModelResponse) -> float:
    """USD cost of a response, from its token counts. 0.0 for unpriced models."""
    return compute_cost_usd(response.model_id, response.prompt_tokens, response.completion_tokens)


@runtime_checkable
class ModelProvider(Protocol):
    """Anything that can turn a request into a response."""

    name: str
    available: bool

    def generate(self, request: ModelRequest) -> ModelResponse:  # pragma: no cover
        ...

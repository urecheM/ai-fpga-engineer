"""Provider-neutral request/response types and the provider interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from ..config.schema import ModelConfig


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

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@runtime_checkable
class ModelProvider(Protocol):
    """Anything that can turn a request into a response."""

    name: str
    available: bool

    def generate(self, request: ModelRequest) -> ModelResponse:  # pragma: no cover
        ...

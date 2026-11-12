from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from ..config.schema import ModelConfig
from ..registry.pricing import compute_cost_usd


@dataclass(frozen=True)
class ModelRequest:

    system: str
    prompt: str
    config: ModelConfig
    context: dict[str, Any] = field(default_factory=dict)
    trial: int = 0
    run_seed: int = 0

def derive_run_seed(exp_seed: int, model: str, benchmark: str, trial: int) -> int:
    """reproducible seed for one trial

    sha256 of the four identifiers, truncated to 31 bits so the seed is valid
    for every RNG and API that accepts one. Same inputs = same seed, any
    change (including the trial index) = an unrelated seed.
    """
    key = f"{exp_seed}|{model}|{benchmark}|{trial}".encode()
    return int(hashlib.sha256(key).hexdigest()[:8], 16) & 0x7FFFFFFF

@dataclass(frozen=True)
class ModelResponse:
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
    return compute_cost_usd(response.model_id, response.prompt_tokens, response.completion_tokens)


@runtime_checkable
class ModelProvider(Protocol):
    name: str
    available: bool

    def generate(self, request: ModelRequest) -> ModelResponse:
        ...

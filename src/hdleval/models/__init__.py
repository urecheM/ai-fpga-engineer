"""Model-inference subsystem.

Inference is fully decoupled from evaluation: a provider only turns a
:class:`ModelRequest` into a :class:`ModelResponse`. New language models are
added by implementing :class:`ModelProvider` and registering it — evaluation
logic never changes.
"""
from __future__ import annotations

from .base import ModelProvider, ModelRequest, ModelResponse
from .reference import ReferenceProvider
from .registry import build_provider, register_provider, available_providers

__all__ = [
    "ModelProvider",
    "ModelRequest",
    "ModelResponse",
    "ReferenceProvider",
    "build_provider",
    "register_provider",
    "available_providers",
]

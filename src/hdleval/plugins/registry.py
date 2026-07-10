"""A tiny typed plugin registry keyed by capability kind."""
from __future__ import annotations

from enum import Enum
from typing import Any, Callable


class PluginKind(str, Enum):
    MODEL = "model"
    AGENT = "agent"
    EVALUATOR = "evaluator"
    BENCHMARK_PROVIDER = "benchmark_provider"
    OPTIMIZATION_PASS = "optimization_pass"
    SYNTHESIS_BACKEND = "synthesis_backend"
    VERIFICATION_ENGINE = "verification_engine"
    DOC_GENERATOR = "doc_generator"


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[PluginKind, dict[str, Callable[..., Any]]] = {
            k: {} for k in PluginKind
        }

    def register(self, kind: PluginKind, name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def deco(factory: Callable[..., Any]) -> Callable[..., Any]:
            self._plugins[kind][name] = factory
            return factory
        return deco

    def get(self, kind: PluginKind, name: str) -> Callable[..., Any]:
        try:
            return self._plugins[kind][name]
        except KeyError as exc:
            raise KeyError(f"no {kind.value} plugin named {name!r}") from exc

    def names(self, kind: PluginKind) -> list[str]:
        return sorted(self._plugins[kind])


registry = PluginRegistry()

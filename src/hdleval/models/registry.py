"""Provider registry: build a provider from a :class:`ModelConfig`."""

from __future__ import annotations

from collections.abc import Callable

from ..config.schema import ConfigError, ModelConfig
from .base import ModelProvider
from .reference import ReferenceProvider

_FACTORIES: dict[str, Callable[[ModelConfig], ModelProvider]] = {}


def register_provider(name: str, factory: Callable[[ModelConfig], ModelProvider]) -> None:
    _FACTORIES[name] = factory


def available_providers() -> list[str]:
    return sorted(_FACTORIES)


def build_provider(cfg: ModelConfig) -> ModelProvider:
    if cfg.provider not in _FACTORIES:
        raise ConfigError(
            f"no provider registered for {cfg.provider!r}; have {available_providers()}"
        )
    return _FACTORIES[cfg.provider](cfg)


def _reference_factory(_: ModelConfig) -> ModelProvider:
    return ReferenceProvider()


def _anthropic_factory(cfg: ModelConfig) -> ModelProvider:
    from .anthropic_provider import AnthropicProvider

    return AnthropicProvider(model_id=cfg.model_id or "claude-sonnet-4-6")


register_provider("reference", _reference_factory)
register_provider("anthropic", _anthropic_factory)


def _synthetic_factory(cfg: ModelConfig) -> ModelProvider:
    from .synthetic import synthetic_factory

    return synthetic_factory(cfg)


register_provider("synthetic", _synthetic_factory)


def _rule_based_factory(cfg: ModelConfig) -> ModelProvider:
    from .rule_based import rule_based_factory

    return rule_based_factory(cfg)


register_provider("rule_based", _rule_based_factory)

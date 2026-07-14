"""Plugin architecture for interchangeable components.

Agents, models, evaluation modules, benchmark providers, optimization passes,
synthesis backends, verification engines and documentation generators are all
registered through :class:`PluginRegistry`, so external researchers extend the
platform without editing the core.
"""

from __future__ import annotations

from .registry import PluginKind, PluginRegistry, registry

__all__ = ["PluginKind", "PluginRegistry", "registry"]

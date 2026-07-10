"""LLM provider seam (offline by default).

The pipeline is rule-based and fully functional without any model: every stage
is deterministic and tool-backed. This module exists so an LLM can later be
attached to ONE narrow, evaluable role (e.g. repairing mutants the rule-based
debugger cannot fix, benchmarked against that baseline) without rewiring the
agents — they all accept a provider but never require one.
"""
from __future__ import annotations


class LLMProvider:
    name = "offline/rule-based"

    def complete(self, prompt: str) -> str:  # pragma: no cover
        raise NotImplementedError(
            "No LLM configured. The pipeline is rule-based and does not need "
            "one; attach a provider here only for a specific, benchmarked "
            "experiment (see docs/CLAIMS.md).")


def get_provider() -> LLMProvider:
    return LLMProvider()

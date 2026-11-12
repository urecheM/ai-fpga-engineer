#offline by default
from __future__ import annotations

class LLMProvider:
    name = "offline/rule-based"

    def complete(self, prompt: str) -> str:
        raise NotImplementedError(
            "No LLM configured")

def get_provider() -> LLMProvider:
    return LLMProvider()

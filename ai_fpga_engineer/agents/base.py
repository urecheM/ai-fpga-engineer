from __future__ import annotations

class Agent:
    name = "agent"

    def __init__(self, llm=None):
        self.llm = llm

    def log(self, project, message: str, level: str = "info") -> None:
        project.log(self.name, message, level)

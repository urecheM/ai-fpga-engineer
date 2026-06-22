"""Project workspace"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import time

from .spec import Specification


@dataclass
class Event:
    agent: str
    message: str
    level: str = "info"          # info | warn | error | success
    t: float = field(default_factory=time.time)


@dataclass
class Project:
    name: str
    root: Path
    request: str = ""
    spec: Specification | None = None
    artifacts: dict[str, str] = field(default_factory=dict)   # label -> relative path
    metrics: dict[str, Any] = field(default_factory=dict)
    events: list[Event] = field(default_factory=list)
    quiet: bool = False

    SUBDIRS = ("rtl", "tb", "sim", "diagrams", "docs", "reports", "memory")

    def init(self) -> "Project":
        self.root.mkdir(parents=True, exist_ok=True)
        for d in self.SUBDIRS:
            (self.root / d).mkdir(exist_ok=True)
        return self

    def log(self, agent: str, message: str, level: str = "info") -> None:
        self.events.append(Event(agent, message, level))
        if self.quiet:
            return
        tag = {"info": "·", "warn": "!", "error": "✗", "success": "✓"}.get(level, "·")
        print(f"  {tag} [{agent}] {message}")

    def write(self, rel: str, content: str, label: str | None = None) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        if label:
            self.artifacts[label] = rel
        return p

    def write_bytes(self, rel: str, content: bytes, label: str | None = None) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
        if label:
            self.artifacts[label] = rel
        return p

    def save_manifest(self) -> Path:
        manifest = {
            "name": self.name,
            "request": self.request,
            "artifacts": self.artifacts,
            "metrics": self.metrics,
            "events": [vars(e) for e in self.events],
        }
        if self.spec:
            manifest["spec"] = self.spec.to_dict()
        return self.write("manifest.json", json.dumps(manifest, indent=2))

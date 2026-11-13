from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LEVEL_TAG = {"info": "  ", "success": "ok", "warn": "! ", "error": "!!"}

@dataclass
class Event:
    when: str
    agent: str
    level: str
    message: str

    def to_dict(self) -> dict:
        return {"when": self.when, "agent": self.agent,
                "level": self.level, "message": self.message}


class Project:
    def __init__(self, name: str, root: str | Path, request: str = "",
                 quiet: bool = False):
        self.name = name
        self.root = Path(root)
        self.request = request
        self.quiet = quiet
        self.events: list[Event] = []
        self.artifacts: dict[str, str] = {}
        self.metrics: dict[str, Any] = {}
        self.context = None

    def init(self) -> "Project":
        self.root.mkdir(parents=True, exist_ok=True)
        for sub in ("rtl", "tb", "docs", "reports"):
            (self.root / sub).mkdir(exist_ok=True)
        return self

    def write(self, rel: str, text: str, label: str | None = None) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        if label:
            self.artifacts[label] = rel
        return path

    def log(self, agent: str, message: str, level: str = "info") -> None:
        ev = Event(datetime.now(timezone.utc).strftime("%H:%M:%S"),
                   agent, level, message)
        self.events.append(ev)
        if not self.quiet:
            print(f"  [{_LEVEL_TAG.get(level, '  ')}] {agent:<18} {message}")

    def save_manifest(self) -> Path:
        manifest = {
            "project": self.name,
            "request": self.request,
            "generated": datetime.now(timezone.utc).isoformat(),
            "artifacts": self.artifacts,
            "metrics": self.metrics,
            "events": [e.to_dict() for e in self.events],
        }
        return self.write("reports/manifest.json",
                          json.dumps(manifest, indent=2, default=str), "manifest")

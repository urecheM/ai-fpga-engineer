"""Machine-readable stage logging.

Every stage of every benchmark execution emits a JSON line. Logs are the raw
substrate from which reports and leaderboards are regenerated, so they are
append-only and self-describing (schema_version + timestamp on each record).
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, TextIO

from .. import SCHEMA_VERSION


@dataclass
class StageEvent:
    experiment: str
    run_id: str
    benchmark: str
    stage: str
    status: str
    duration_s: float = 0.0
    detail: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)
    schema_version: str = SCHEMA_VERSION

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


class StructuredLogger:
    def __init__(self, path: str | Path | None = None, echo: bool = False) -> None:
        self._fh: TextIO | None = None
        if path is not None:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            self._fh = p.open("a", encoding="utf-8")
        self._echo = echo

    def log(self, event: StageEvent) -> None:
        line = event.to_json()
        if self._fh is not None:
            self._fh.write(line + "\n")
            self._fh.flush()
        if self._echo:
            sys.stderr.write(f"[{event.benchmark}:{event.stage}] {event.status}\n")

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def __enter__(self) -> StructuredLogger:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

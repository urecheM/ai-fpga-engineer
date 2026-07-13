"""Experiment provenance record.

Records every fact needed to reproduce a run: model version, prompt template,
benchmark version, compiler/synth/verifier, OS, hardware, git commit, timestamp,
random seed, inference config, duration, retry history and produced artifacts.
"""

from __future__ import annotations

import platform
import subprocess
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from .. import SCHEMA_VERSION


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def environment_fingerprint() -> dict[str, str]:
    """Capture the host environment for reproducibility."""
    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "git_commit": _git_commit(),
    }


@dataclass
class ExperimentRecord:
    experiment: str
    run_id: str
    benchmark: str
    benchmark_version: str
    model: str
    model_id: str
    prompt: str
    seed: int
    trial: int
    inference_config: dict[str, Any] = field(default_factory=dict)
    toolchain: dict[str, str] = field(default_factory=dict)
    environment: dict[str, str] = field(default_factory=environment_fingerprint)
    started_at: float = field(default_factory=time.time)
    duration_s: float = 0.0
    retry_history: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    failure_class: str = "none"
    passed: bool = False
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

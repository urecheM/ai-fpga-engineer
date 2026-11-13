from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return ROOT


def reference_verdict_ok(result) -> bool:
    from hdleval.toolchain.detect import detect

    if detect().has("ghdl"):
        return bool(result.passed)
    return (not result.passed) and result.failure_class == "unverified"


@pytest.fixture
def suite():
    from hdleval.benchmarks.loader import load_suite

    return load_suite("v1")

"""Load benchmark metadata from ``benchmarks/<version>/<id>/benchmark.yaml``."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from ..config.schema import BenchmarkSelector
from .difficulty import difficulty_score
from .schema import Benchmark, ComplexityMetrics, Port


def benchmarks_root(explicit: str | os.PathLike[str] | None = None) -> Path:
    if explicit is not None:
        return Path(explicit)
    env = os.environ.get("HDLEVAL_BENCHMARKS_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3] / "benchmarks"


def load_benchmark(bench_dir: str | os.PathLike[str]) -> Benchmark:
    bdir = Path(bench_dir)
    d = yaml.safe_load((bdir / "benchmark.yaml").read_text())
    comp = ComplexityMetrics(**d.get("complexity", {}))
    ports = [Port(**p) for p in d.get("interfaces", [])]
    est = d.get("estimated_difficulty", 0) or difficulty_score(comp)
    return Benchmark(
        id=d["id"],
        version=d["version"],
        category=d["category"],
        title=d["title"],
        specification=d["specification"].strip(),
        functional_requirements=d.get("functional_requirements", []),
        expected_behavior=d.get("expected_behavior", ""),
        entity=d.get("entity", ""),
        interfaces=ports,
        tags=d.get("tags", []),
        complexity=comp,
        reference_hdl_path=d.get("reference_hdl_path", ""),
        testbench_path=d.get("testbench_path", ""),
        testbench_entity=d.get("testbench_entity", ""),
        properties=d.get("properties", []),
        estimated_difficulty=est,
    )


def load_suite(version: str = "v1", root: str | os.PathLike[str] | None = None) -> list[Benchmark]:
    base = benchmarks_root(root) / version
    if not base.exists():
        return []
    out: list[Benchmark] = []
    for bdir in sorted(base.iterdir()):
        if (bdir / "benchmark.yaml").exists():
            out.append(load_benchmark(bdir))
    return out


def select(benchmarks: list[Benchmark], sel: BenchmarkSelector) -> list[Benchmark]:
    def keep(b: Benchmark) -> bool:
        if sel.ids and b.id not in sel.ids:
            return False
        if sel.categories and b.category not in sel.categories:
            return False
        return sel.difficulty_min <= b.estimated_difficulty <= sel.difficulty_max

    return [b for b in benchmarks if keep(b)]


def _suite_dir(b: Benchmark) -> str:
    """Map a benchmark's semantic version to its suite directory (1.x -> v1)."""
    return f"v{b.version.split('.')[0]}"


def reference_hdl(b: Benchmark, root: str | os.PathLike[str] | None = None) -> str:
    if not b.reference_hdl_path:
        return ""
    p = benchmarks_root(root) / _suite_dir(b) / b.id / b.reference_hdl_path
    return p.read_text() if p.exists() else ""


def testbench_hdl(b: Benchmark, root: str | os.PathLike[str] | None = None) -> str:
    if not b.testbench_path:
        return ""
    p = benchmarks_root(root) / _suite_dir(b) / b.id / b.testbench_path
    return p.read_text() if p.exists() else ""

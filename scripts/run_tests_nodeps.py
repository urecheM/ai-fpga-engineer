"""Run the pytest suite without pytest installed (offline verification shim).

Provides a minimal `pytest` module (fixture, raises) + fixtures (tmp_path,
repo_root, suite), discovers test_* functions, and reports pass/fail. This is a
convenience for environments without the dev extras; CI uses real pytest+coverage.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
import tempfile
import traceback
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


# --- fake pytest ---
class _Raises:
    def __init__(self, exc):
        self.exc = exc

    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        if et is None:
            raise AssertionError(f"expected {self.exc.__name__}")
        return issubclass(et, self.exc)


pytest = types.ModuleType("pytest")
pytest.raises = lambda exc: _Raises(exc)


def _fixture(*a, **k):
    def deco(fn):
        fn.__is_fixture__ = True
        return fn

    return deco if not a else deco(a[0])


pytest.fixture = _fixture
sys.modules["pytest"] = pytest


def _make_fixtures(tmp_root):
    from hdleval.benchmarks.loader import load_suite

    counter = {"n": 0}

    def tmp_path():
        counter["n"] += 1
        p = Path(tmp_root) / f"t{counter['n']}"
        p.mkdir(parents=True, exist_ok=True)
        return p

    return {
        "repo_root": lambda: ROOT,
        "suite": lambda: load_suite("v1"),
        "tmp_path": tmp_path,
    }


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    tmp_root = tempfile.mkdtemp()
    fixtures = _make_fixtures(tmp_root)
    test_files = sorted((ROOT / "tests").rglob("test_*.py"))
    passed = failed = 0
    failures = []
    for tf in test_files:
        mod = _load(tf)
        for name, fn in inspect.getmembers(mod, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            if getattr(fn, "__is_fixture__", False):
                continue
            sig = inspect.signature(fn)
            kwargs = {p: fixtures[p]() for p in sig.parameters if p in fixtures}
            try:
                fn(**kwargs)
                passed += 1
            except Exception as e:
                failed += 1
                failures.append(f"{tf.name}::{name}: {e}")
                traceback.print_exc()
    print(f"\n{'=' * 50}\nPASSED {passed}  FAILED {failed}")
    for f in failures:
        print("  FAIL", f)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

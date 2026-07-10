"""Approximate statement coverage of hdleval using sys.settrace (no deps).

Not a substitute for coverage.py (used in CI) but gives a realistic figure for
the README when the dev extras are unavailable.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "src" / "hdleval"
sys.path.insert(0, str(ROOT / "src"))

executed: dict[str, set[int]] = {}


def _tracer(frame, event, arg):
    if event == "line":
        fn = frame.f_code.co_filename
        if str(PKG) in fn:
            executed.setdefault(fn, set()).add(frame.f_lineno)
    return _tracer


def statement_lines(path: Path) -> set[int]:
    tree = ast.parse(path.read_text())
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt) and not isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import,
                   ast.ImportFrom)
        ):
            lines.add(node.lineno)
    return lines


def main() -> int:
    import scripts.run_tests_nodeps as runner  # noqa
    sys.settrace(_tracer)
    runner.main()
    sys.settrace(None)

    total = covered = 0
    per_file = []
    for py in sorted(PKG.rglob("*.py")):
        if py.name == "anthropic_provider.py":
            continue
        stmts = statement_lines(py)
        ex = executed.get(str(py), set())
        hit = len(stmts & ex)
        total += len(stmts)
        covered += hit
        pct = 100 * hit / len(stmts) if stmts else 100
        per_file.append((pct, py.relative_to(PKG), hit, len(stmts)))
    for pct, rel, hit, n in sorted(per_file):
        print(f"{pct:5.0f}%  {str(rel):40s} {hit}/{n}")
    overall = 100 * covered / total if total else 0
    print(f"\nOVERALL: {overall:.1f}%  ({covered}/{total} statements)")
    Path(ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "coverage.txt").write_text(f"{overall:.1f}")
    return 0


if __name__ == "__main__":
    main()

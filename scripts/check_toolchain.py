"""python scripts/check_toolchain.py
python scripts/check_toolchain.py --synthesize
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hdleval.toolchain.detect import detect
from hdleval.toolchain.yosys import synthesize

V1 = ROOT / "benchmarks" / "v1"


def assert_toolchain() -> int:
    summary = detect(refresh=True).summary()
    print(f"toolchain: {summary}")
    if "ghdl-yosys-plugin=yes" not in summary:
        print(
            "FAIL: ghdl-yosys-plugin is not loadable by Yosys. Every synthesis "
            "stage would report status='skipped' and resource metrics would be "
            "unmeasured. Install the OSS CAD Suite and put its bin/ on PATH.",
            file=sys.stderr,
        )
        return 1
    print("OK: ghdl-yosys-plugin=yes")
    return 0


def synthesize_suite() -> int:
    designs = sorted(V1.glob("*/benchmark.yaml"))
    if not designs:
        print(f"FAIL: no benchmarks found under {V1}", file=sys.stderr)
        return 1

    failures: list[str] = []
    total_luts = total_ffs = 0.0
    print(f"\n{'benchmark':22s} {'entity':16s} {'status':8s} {'luts':>6s} {'ffs':>6s}")
    for meta_path in designs:
        meta = yaml.safe_load(meta_path.read_text())
        ref = meta_path.parent / meta.get("reference_hdl_path", "")
        if not ref.is_file():
            failures.append(f"{meta['id']}: missing reference HDL at {ref}")
            continue
        result = synthesize(ref.read_text(), meta["entity"])
        luts = result.metrics.get("luts", 0.0)
        ffs = result.metrics.get("ffs", 0.0)
        print(f"{meta['id']:22s} {meta['entity']:16s} {result.status:8s} {luts:6.0f} {ffs:6.0f}")
        if not result.ok:
            failures.append(
                f"{meta['id']}: synthesis {result.status} — {result.stderr.strip()[:200]}"
            )
            continue
        if luts <= 0:
            failures.append(f"{meta['id']}: synthesized but reported 0 LUTs")
        total_luts += luts
        total_ffs += ffs

    print(f"\ntotal: luts={total_luts:.0f} ffs={total_ffs:.0f} over {len(designs)} designs")
    if total_ffs <= 0:
        failures.append("no flip-flops counted across the whole suite")
    if failures:
        print("\nFAIL:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("OK: every reference design synthesized with non-zero cell counts")
    return 0


def main(argv: list[str]) -> int:
    rc = assert_toolchain()
    if rc or "--synthesize" not in argv:
        return rc
    return synthesize_suite()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

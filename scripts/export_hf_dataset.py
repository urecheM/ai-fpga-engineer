"""Export the v1 benchmark suite as a Hugging Face-ready dataset.

Emits `external/huggingface/data/benchmarks.jsonl` (one benchmark per line, with
reference HDL inlined) plus a `dataset_infos`-style summary. The dataset is a
build product of `benchmarks/v1/`, never hand-maintained.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hdleval.benchmarks.loader import load_suite, reference_hdl  # noqa: E402

OUT = ROOT / "external" / "huggingface" / "data"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    suite = load_suite("v1")
    with (OUT / "benchmarks.jsonl").open("w") as fh:
        for b in suite:
            row = b.to_dict()
            row["reference_hdl"] = reference_hdl(b)
            fh.write(json.dumps(row) + "\n")
    cats = sorted({b.category for b in suite})
    summary = {
        "n_benchmarks": len(suite),
        "categories": cats,
        "difficulty_range": [min(b.estimated_difficulty for b in suite),
                             max(b.estimated_difficulty for b in suite)],
        "suite_version": "v1",
    }
    (OUT.parent / "dataset_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"exported {len(suite)} benchmarks to {OUT}")


if __name__ == "__main__":
    main()

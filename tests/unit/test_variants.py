from __future__ import annotations

import sys

from conftest import ROOT

sys.path.insert(0, str(ROOT / "scripts"))

from build_variants import derived
from hdleval.benchmarks import loader


def test_derived_placeholders():
    assert derived({"W": 12}) == {"W": "12", "W1": "11"}
    d = derived({"PATTERN": "10010"})
    assert (d["N"], d["N1"], d["N2"], d["N3"]) == ("5", "4", "3", "2")


def test_committed_variant_suite_is_complete():
    suite = loader.load_suite("v1-variants")
    assert suite, "run scripts/build_variants.py --release-seed <seed>"
    for b in suite:
        assert b.suite == "v1-variants"
        assert loader.reference_hdl(b) and loader.testbench_hdl(b), b.id
from __future__ import annotations

import random

import pytest

from hdleval.benchmarks.loader import load_suite, reference_hdl
from hdleval.models.faults import SEMANTIC, apply_fault
from hdleval.toolchain import compile_vhdl
from hdleval.toolchain.detect import detect


def test_every_semantic_operator_applies_somewhere():
    refs = [reference_hdl(b) for b in load_suite("v1")]
    for name, op in SEMANTIC.items():
        assert any(op(r, random.Random(0)) not in (None, r) for r in refs), name


def test_apply_fault_is_seeded():
    ref = reference_hdl(next(b for b in load_suite("v1") if b.id == "fsm_seqdet"))
    a = apply_fault(ref, "semantic", random.Random(3))
    b = apply_fault(ref, "semantic", random.Random(3))
    assert a == b and a[0] != ref


@pytest.mark.skipif(not detect().has("ghdl"), reason="ghdl not installed")
def test_semantic_mutants_still_compile():
    for bench in load_suite("v1"):
        ref = reference_hdl(bench)
        for name, op in SEMANTIC.items():
            mut = op(ref, random.Random(0))
            if mut is None:
                continue
            res = compile_vhdl(mut, entity=bench.entity)
            assert res.status == "ok", f"{bench.id}/{name}: {res.stderr[:200]}"
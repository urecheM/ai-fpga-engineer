from __future__ import annotations

import random
import shutil

import pytest

from hdleval.benchmarks.loader import load_suite, reference_hdl
from hdleval.models.faults import swap_operator
from hdleval.parsing.ports import parse_ports
from hdleval.verification.equivalence import check_equivalence, miter_vhdl, rename_entity

needs_sby = pytest.mark.skipif(not shutil.which("sby"), reason="SymbiYosys not installed")


def _bench(bid: str):
    return next(b for b in load_suite("v1") if b.id == bid)


def test_miter_text_has_both_instances_and_reset_assumption():
    b = _bench("fsm_seqdet")
    m = miter_vhdl(b.entity, parse_ports(reference_hdl(b), b.entity))
    assert "entity work.seq_detect port map" in m and "seq_detect_ref" in m
    assert "assume always (first = '1' -> rst = '1')" in m
    assert "rename" not in rename_entity(reference_hdl(b), b.entity, "x_ref")


@needs_sby
def test_reference_is_equivalent_to_itself():
    b = _bench("arith_adder8")
    assert check_equivalence(reference_hdl(b), reference_hdl(b), b.entity).status == "proven"


@needs_sby
def test_semantic_mutant_is_not_equivalent():
    b = _bench("arith_adder8")
    mut = swap_operator(reference_hdl(b), random.Random(0))
    assert check_equivalence(mut, reference_hdl(b), b.entity).status == "fail"
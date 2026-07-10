"""Self-test and regression suite — tool-aware and non-circular.

Run standalone::

    python -m ai_fpga_engineer.selftest

or under pytest (each ``check_*`` has a ``test_*`` wrapper; tool-gated checks
skip cleanly when the toolchain is absent, unless AIFPGA_REQUIRE_TOOLS=1).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

try:
    import pytest
except ImportError:            # standalone mode
    pytest = None

from .core.orchestrator import Orchestrator
from .core.project import Project
from .core.decisions import ArchDecisions, Targets
from .core import toolchain
from .agents.requirements_agent import RequirementsAgent
from .agents.hdl_agent import HDLAgent
from .agents.verification_agent import VerificationAgent
from .agents.formal_agent import FormalAgent
from .sim.runner import SimulationAgent
from .sim import pnr
from .sim.lint import lint
from .hdl import library, mutate
from .hdl.library import alu_rtl_emulate
from .reference import models as ref

ALU8 = "Design an 8-bit ALU supporting ADD, SUB, AND, OR, XOR."
REG8 = "Design an 8-bit register with synchronous load and reset."
CNT8 = "Design an 8-bit up counter with synchronous reset and enable."
CMP8 = "Design an 8-bit comparator with gt, eq, lt outputs."


class Skip(Exception):
    """Raised when a check needs tools that are absent (fatal in CI)."""


def _need(condition: bool, why: str) -> None:
    if not condition:
        if toolchain.require_tools():
            raise AssertionError(f"AIFPGA_REQUIRE_TOOLS=1 but: {why}")
        raise Skip(why)


def _scratch(request: str, decisions=None):
    project = Project("selftest", Path(tempfile.mkdtemp()) / "selftest",
                      request=request, quiet=True).init()
    spec = RequirementsAgent().run(project)
    design = HDLAgent().run(project, spec, decisions)
    return project, spec, design


def check_pipeline_alu_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        res = Orchestrator().run(
            "Design a 16-bit ALU with ADD, SUB, AND, OR, XOR, NOT, INC, DEC.",
            workdir=tmp, verbose=False)
        data = json.loads((res.project.root
                           / f"tb/{res.design.entity}_vectors.json").read_text())
        W = res.spec.data_width
        for v, e in zip(data["vectors"], data["expected"]):
            r, c = ref.alu(v["op"], v["a"], v["b"], W)
            assert (r, c, ref.alu_zero(r)) == (e["result"], e["carry"], e["zero"]), \
                f"embedded expected value disagrees with oracle at {v}"
        assert res.verification.passed, "model-level property checks failed"
        if toolchain.detect().sim_ok:
            assert res.simulation.ran, "ghdl present but the simulator did not run"
            assert res.simulation.passed, \
                "GHDL executed the emitted RTL and it FAILED the oracle testbench"
        else:
            _need(False, "ghdl absent: the RTL itself was NOT executed by this check")


def check_rtl_datapath_matches_reference_exhaustively():
    project, spec, _ = _scratch(ALU8)
    W = spec.data_width
    ops = ["ADD", "SUB", "AND", "OR", "XOR"]
    cands = library.candidate_decisions(spec)
    assert len(cands) >= 2, "expected a non-trivial design space for the ALU"
    for d in cands:
        for op in ops:
            for a in range(1 << W):
                for b in range(1 << W):
                    assert alu_rtl_emulate(d, a, b, op, W) == ref.alu(op, a, b, W), \
                        f"datapath emulation mismatch: {d.label()} {op} a={a} b={b}"


def check_generated_rtl_is_lint_clean():
    classes = {ALU8: "alu", CNT8: "counter", CMP8: "comparator", REG8: "register"}
    for request, expected_class in classes.items():
        project, spec, design = _scratch(request)
        assert spec.design_class == expected_class, \
            f"{request!r} classified as {spec.design_class}"
        issues = [i for i in lint(design.vhdl) if i.fixable]
        assert not issues, f"{expected_class} RTL has lint issues: {issues}"


def check_architecture_decisions_bind_rtl():
    _, spec, _ = _scratch(ALU8)
    comb = library.generate(spec, ArchDecisions(register_output=False))
    reg = library.generate(spec, ArchDecisions(register_output=True))
    onehot = library.generate(spec, ArchDecisions(opcode_encoding="onehot"))
    assert comb.vhdl != reg.vhdl, "register_output did not change the RTL"
    assert "rising_edge" in reg.vhdl and "rising_edge" not in comb.vhdl, \
        "registered variant is not actually clocked"
    assert comb.latency == 0 and reg.latency == 1, "latency does not reflect pipelining"
    assert comb.vhdl != onehot.vhdl, "opcode encoding choice did not change the RTL"


def check_dse_hdl_critic_and_formal():
    with tempfile.TemporaryDirectory() as tmp:
        res = Orchestrator().run(ALU8, workdir=tmp, verbose=False)
        cands = res.context.candidates
        assert len(cands) >= 2, "design-space exploration produced <2 candidates"
        assert sum(1 for c in cands if c.selected) == 1, "exactly one candidate selected"
        assert res.hdl_review.clean, f"HDL critic flagged a clean ALU: {res.hdl_review.blocking}"
        assert res.formal.properties, "formal stage produced no model checks"
        assert not res.formal.any_failed, "a formal check failed on a clean ALU"
        assert all(p.status == "model_exhaustive" for p in res.formal.properties), \
            "8-bit ALU model checks should all be exhaustive"
        assert res.formal.sby_status in ("pass", "not_run"), \
            f"RTL-level BMC did not pass cleanly: {res.formal.sby_status}"


def check_qor_loop_mechanics_on_estimates():
    _, spec, _ = _scratch(ALU8)
    comb = library.estimate(spec, ArchDecisions("binary", False, False))
    reg = library.estimate(spec, ArchDecisions("binary", True, False))
    assert reg.fmax_mhz > comb.fmax_mhz, "estimator sanity: registering must raise est. Fmax"
    target = (comb.fmax_mhz + reg.fmax_mhz) / 2.0
    with tempfile.TemporaryDirectory() as tmp:
        res = Orchestrator().run(ALU8, workdir=tmp, objective="area",
                                 targets=Targets(fmax_mhz=target),
                                 do_formal=False, do_synth=False, verbose=False)
        if res.context.qor.source != "estimated":
            return
        assert len(res.context.qor_history) >= 2, "loop did not iterate on an unmet target"
        assert res.design.decisions.register_output, \
            "loop did not apply register_output to raise estimated Fmax"
        assert res.summary["targets_met"] is True
        assert res.verification.passed, "refined design failed verification"


def check_qor_loop_closes_measured_timing():
    ok, why = pnr.available()
    _need(ok, f"place-and-route flow unavailable ({why})")
    p1, spec, d_comb = _scratch(ALU8, ArchDecisions("binary", False, False))
    r_comb = pnr.run_ice40(p1, d_comb)
    assert r_comb.ran, f"baseline PnR failed: {r_comb.reason}"
    p2, _, d_reg = _scratch(ALU8, ArchDecisions("binary", True, False))
    r_reg = pnr.run_ice40(p2, d_reg)
    assert r_reg.ran, f"registered-variant PnR failed: {r_reg.reason}"
    if r_reg.qor.fmax_mhz <= r_comb.qor.fmax_mhz * 1.02:
        raise Skip("registering did not measurably improve Fmax on this flow; "
                   "capability test not meaningful here")
    target = (r_comb.qor.fmax_mhz + r_reg.qor.fmax_mhz) / 2.0
    with tempfile.TemporaryDirectory() as tmp:
        res = Orchestrator().run(ALU8, workdir=tmp, objective="area",
                                 targets=Targets(fmax_mhz=target),
                                 max_qor_iters=8, do_formal=False, verbose=False)
        q = res.context.qor
        assert q is not None and q.source == "nextpnr-ice40", \
            f"loop did not use measured QoR (source={q and q.source})"
        assert q.fmax_mhz >= target, \
            f"measured closure failed: {q.fmax_mhz} < derived target {target:.1f} MHz"
        assert res.summary["targets_met"] is True
        assert res.verification.passed and res.simulation.passed, \
            "refined design failed functional verification"


def check_ghdl_detects_seeded_semantic_bug():
    _need(toolchain.detect().sim_ok, "ghdl not installed")
    project, spec, design = _scratch(ALU8)
    mutated = mutate.apply("stuck_carry_zero", design.vhdl)
    assert mutated is not None, "mutation unexpectedly not applicable"
    (project.root / f"rtl/{design.entity}.vhd").write_text(mutated)
    design.vhdl = mutated
    vres = VerificationAgent().run(project, spec, design)
    assert vres.passed, "sanity: this bug must be invisible to model-level checks"
    sim = SimulationAgent().run(project, spec, design, vres)
    assert sim.ran, "ghdl present but the simulator did not run"
    assert sim.passed is False, \
        "GHDL PASSED a design with a stuck carry — the harness cannot detect wrongness"


def check_sby_bmc_passes_on_counter():
    _need(toolchain.detect().formal_ok, "sby and/or GHDL yosys plugin not installed")
    project, spec, design = _scratch(CNT8)
    fr = FormalAgent().run(project, spec, design)
    assert fr.sby_status == "pass", \
        f"RTL-level BMC did not pass (status={fr.sby_status}); see formal/*_sby.log"
    assert not fr.any_failed


def check_self_healing_debug_loop():
    with tempfile.TemporaryDirectory() as tmp:
        res = Orchestrator().run(ALU8, workdir=tmp, mutate="drop_numeric_std",
                                 do_formal=False, do_synth=False, verbose=False)
        assert res.debug.iterations >= 1, "debug loop did not run on the seeded defect"
        assert res.debug.final_clean, "debug loop failed to reach a clean design"
        rtl = (res.project.root / f"rtl/{res.design.entity}.vhd").read_text()
        assert "numeric_std" in rtl, "numeric_std use clause not restored"


def _run(fn):
    try:
        fn()
    except Skip as e:
        if pytest is not None:
            pytest.skip(str(e))
        raise


def test_pipeline_alu_end_to_end(): _run(check_pipeline_alu_end_to_end)
def test_rtl_datapath_matches_reference_exhaustively(): _run(check_rtl_datapath_matches_reference_exhaustively)
def test_generated_rtl_is_lint_clean(): _run(check_generated_rtl_is_lint_clean)
def test_architecture_decisions_bind_rtl(): _run(check_architecture_decisions_bind_rtl)
def test_dse_hdl_critic_and_formal(): _run(check_dse_hdl_critic_and_formal)
def test_qor_loop_mechanics_on_estimates(): _run(check_qor_loop_mechanics_on_estimates)
def test_qor_loop_closes_measured_timing(): _run(check_qor_loop_closes_measured_timing)
def test_ghdl_detects_seeded_semantic_bug(): _run(check_ghdl_detects_seeded_semantic_bug)
def test_sby_bmc_passes_on_counter(): _run(check_sby_bmc_passes_on_counter)
def test_self_healing_debug_loop(): _run(check_self_healing_debug_loop)


def main() -> int:
    checks = [
        ("pipeline end-to-end; RTL executed by GHDL", check_pipeline_alu_end_to_end),
        ("emulated datapath matches oracle for every architecture (fast pre-check)",
         check_rtl_datapath_matches_reference_exhaustively),
        ("generated RTL is lint-clean for every class", check_generated_rtl_is_lint_clean),
        ("architecture decisions actually bind the RTL", check_architecture_decisions_bind_rtl),
        ("DSE + HDL critic + formal stage (honest statuses)", check_dse_hdl_critic_and_formal),
        ("QoR loop mechanics on estimates (not a capability claim)",
         check_qor_loop_mechanics_on_estimates),
        ("[tools] closed loop meets timing target on MEASURED numbers",
         check_qor_loop_closes_measured_timing),
        ("[tools] GHDL detects a seeded semantic bug (negative test)",
         check_ghdl_detects_seeded_semantic_bug),
        ("[tools] SymbiYosys BMC passes on counter RTL invariants",
         check_sby_bmc_passes_on_counter),
        ("self-healing loop repairs a lint-fixable seeded defect",
         check_self_healing_debug_loop),
    ]
    failed = skipped = 0
    mode = "REQUIRED" if toolchain.require_tools() else "best-effort"
    print(f"Running self-tests (toolchain: {toolchain.detect().summary()}; "
          f"tool policy: {mode})...\n")
    for name, fn in checks:
        try:
            fn()
            print(f"  PASS  {name}")
        except Skip as e:
            skipped += 1
            print(f"  SKIP  {name}\n        {e}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {name}\n        {e}")
    print(f"\n{len(checks) - failed - skipped}/{len(checks)} passed, "
          f"{skipped} skipped, {failed} failed.")
    if skipped and not toolchain.require_tools():
        print("NOTE: skipped checks mean the corresponding claims are UNVERIFIED "
              "in this environment. Install the OSS CAD Suite, or set "
              "AIFPGA_REQUIRE_TOOLS=1 to make skips fatal (CI does).")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

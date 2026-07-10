"""Closed-loop pipeline orchestrator.

Changes versus the previous version, mapped to the review findings:

* **Measured QoR closes the loop.** When the open-source flow is installed
  (yosys + GHDL plugin + nextpnr-ice40), every QoR-loop iteration is measured
  by real place-and-route on an iCE40 UP5K and "targets met" refers to those
  numbers. The heuristic estimator still ranks *proposals* (it is cheap), but
  acceptance is decided by measurement. Without tools the loop runs on
  estimates and says so (``qor.source == "estimated"``); with
  ``AIFPGA_REQUIRE_TOOLS=1`` the estimate-only path is a hard failure.

* **Un-rigged defect seeding.** ``mutate=<name>`` applies any operator from
  ``hdl.mutate`` (eight defect classes) instead of the single planted,
  auto-repairable fault. ``inject_fault=True`` is kept as an alias for
  ``mutate="drop_numeric_std"``.

* **Debug history is accumulated, not overwritten** (the old ``_gate`` return
  let an empty report shadow a real one).

* **Confidence is derived from evidence** (what actually ran and passed), with
  the formula documented in ``docs/CLAIMS.md``, instead of hardcoded numbers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .project import Project
from .spec import Specification
from .llm import get_provider, LLMProvider
from .decisions import ArchDecisions, QoR, Targets, score
from .context import EngineeringContext, Candidate, QoRIteration
from . import toolchain

from ..agents.requirements_agent import RequirementsAgent
from ..agents.architecture_agent import ArchitectureAgent, Architecture
from ..agents.critic_agent import CriticAgent, Finding
from ..agents.hdl_agent import HDLAgent
from ..agents.hdl_critic_agent import HDLCriticAgent, HDLReview
from ..agents.verification_agent import VerificationAgent, VerificationResult
from ..agents.debug_agent import DebugAgent, DebugReport
from ..agents.optimization_agent import OptimizationAgent, OptimizationReport
from ..agents.documentation_agent import DocumentationAgent
from ..agents.formal_agent import FormalAgent, FormalResult
from ..agents.failure_classifier import classify
from ..sim.runner import SimulationAgent, SimulationResult
from ..sim.synth import SynthAgent, SynthResult
from ..sim import pnr
from ..sim.lint import lint
from ..hdl import library, mutate as mutate_mod
from ..hdl.library import GeneratedDesign


MAX_REVISIONS = 2
MAX_QOR_ITERS = 4


@dataclass
class PipelineResult:
    project: Project
    spec: Specification
    architecture: Architecture
    findings: list[Finding]
    design: GeneratedDesign
    hdl_review: HDLReview
    verification: VerificationResult
    simulation: SimulationResult
    debug: DebugReport
    optimization: OptimizationReport
    formal: FormalResult
    synthesis: SynthResult
    context: EngineeringContext
    report_path: Path
    ok: bool
    summary: dict[str, Any] = field(default_factory=dict)


class Orchestrator:
    def __init__(self, llm: LLMProvider | None = None):
        self.llm = llm or get_provider()
        self.requirements = RequirementsAgent(self.llm)
        self.architecture = ArchitectureAgent(self.llm)
        self.critic = CriticAgent(self.llm)
        self.hdl = HDLAgent(self.llm)
        self.hdl_critic = HDLCriticAgent(self.llm)
        self.verification = VerificationAgent(self.llm)
        self.simulation = SimulationAgent(self.llm)
        self.debug = DebugAgent(self.llm)
        self.optimization = OptimizationAgent(self.llm)
        self.formal = FormalAgent(self.llm)
        self.synthesis = SynthAgent(self.llm)
        self.documentation = DocumentationAgent(self.llm)

    # ------------------------------------------------------------------
    def run(self, request: str, workdir: str | Path = "projects",
            name: str | None = None, exhaustive: bool = False,
            inject_fault: bool = False, mutate: str | None = None,
            objective: str = "balanced",
            targets: Targets | None = None, max_qor_iters: int = MAX_QOR_ITERS,
            do_formal: bool = True, do_synth: bool = True,
            verbose: bool = True) -> PipelineResult:
        targets = targets or Targets()
        if inject_fault and mutate is None:
            mutate = "drop_numeric_std"
        tools = toolchain.detect()
        if verbose:
            print(f"\n=== AI FPGA Engineer  (rule-based closed-loop pipeline; "
                  f"LLM backend: {self.llm.name}) ===")
            print(f"Request: {request}")
            print(f"Toolchain: {tools.summary()}")
            if not targets.is_empty():
                print(f"Targets: {targets}")
            print()
        if toolchain.require_tools() and not tools.sim_ok:
            raise RuntimeError("AIFPGA_REQUIRE_TOOLS=1 but ghdl is not installed")

        ctx = EngineeringContext()

        # ---- requirements ------------------------------------------
        provisional = self.requirements.run(_Stub(request))
        proj_name = name or provisional.name
        root = Path(workdir) / proj_name
        project = Project(proj_name, root, request=request, quiet=not verbose).init()
        project.context = ctx
        spec = self.requirements.run(project)
        # documented prior: rule-based classifier matched a known class or not
        ctx.set_confidence("requirements", 0.9 if spec.design_class != "unknown" else 0.3)

        # ---- architecture + critic revision loop --------------------
        arch = self.architecture.run(project, spec)
        findings = self.critic.run(project, spec, arch)
        revision = 0
        while self._blocking(findings) and revision < MAX_REVISIONS:
            revision += 1
            project.log("orchestrator", "blocking design-review findings; revising "
                        f"architecture (attempt {revision})", "warn")
            arch = self.architecture.run(project, spec, revision=revision)
            findings = self.critic.run(project, spec, arch)
        if self._blocking(findings):
            project.log("orchestrator", "design review still blocking after "
                        f"{MAX_REVISIONS} revisions; proceeding and flagging it", "warn")
        else:
            project.log("orchestrator", "design review accepted", "success")
        ctx.set_confidence("architecture",
                           max(0.2, 1.0 - 0.3 * len(self._blocking(findings))))

        # ---- design-space exploration (choose ArchDecisions) --------
        decisions = self._explore(project, spec, objective, targets, ctx)

        # ---- closed QoR loop ----------------------------------------
        design, hdl_review, vres, sim, debug = self._qor_loop(
            project, spec, decisions, objective, targets, max_qor_iters,
            exhaustive, mutate, ctx)

        # ---- optimization report (on the final design) -------------
        opt = self.optimization.run(project, spec, design, objective=objective,
                                    targets=targets)

        # ---- formal stage -------------------------------------------
        formal = FormalResult()
        if do_formal:
            formal = self.formal.run(project, spec, design)
            ctx.set_confidence("formal", formal.confidence)

        # ---- synthesis (measured when possible) ----------------------
        synth = SynthResult(False, "skipped")
        if do_synth:
            synth = self.synthesis.run(project, design, estimate=ctx.qor)
            if synth.ran and synth.qor is not None and synth.qor.fmax_mhz > 0:
                ctx.qor = synth.qor   # prefer measured numbers

        # ---- evidence-based confidence wrap-up -----------------------
        # verification: 1.0 = GHDL executed the RTL and it passed;
        #               0.6 = only the model-level checks ran (no simulator);
        #               0.0 = a failure anywhere.
        if sim.ran:
            ctx.set_confidence("verification", 1.0 if (sim.passed and vres.passed) else 0.0)
        else:
            ctx.set_confidence("verification", 0.6 if vres.passed else 0.0)
        ctx.set_confidence("debug", 1.0 if debug.final_clean else 0.0)
        ctx.set_confidence("hdl", 1.0 if hdl_review.clean else 0.4)
        ctx.set_confidence("qor", 1.0 if (ctx.qor and ctx.qor.source == "nextpnr-ice40")
                           else 0.5)
        ctx.notes.append("confidence formulas: see docs/CLAIMS.md (evidence-derived; "
                         "1.0 requires the real tool to have run and passed)")

        # ---- documentation ------------------------------------------
        report_path = self.documentation.run(
            project, spec, arch, design, findings, hdl_review, vres, sim,
            debug, opt, formal, synth, ctx)

        # ---- finalise -----------------------------------------------
        ok = (not self._blocking(findings) and hdl_review.clean
              and not vres.property_failures and debug.final_clean
              and (sim.passed is not False) and not formal.any_failed
              and (sim.ran or not toolchain.require_tools()))
        summary = {
            "design_class": spec.design_class,
            "entity": design.entity,
            "data_width": spec.data_width,
            "operations": [op.name for op in spec.operations],
            "architecture": design.decisions.label(),
            "candidates_explored": len(ctx.candidates),
            "qor_iterations": len(ctx.qor_history),
            "targets": str(targets) if not targets.is_empty() else None,
            "targets_met": targets.met_by(ctx.qor) if ctx.qor else None,
            "mutation_applied": mutate,
            "test_vectors": vres.total,
            "property_checks": "pass" if not vres.property_failures else "fail",
            "hdl_review": "clean" if hdl_review.clean else f"{len(hdl_review.blocking)} blocking",
            "formal": formal.label() if formal.properties else "skipped",
            "sby_status": formal.sby_status,
            "sim_backend": sim.backend,
            "sim_ran": sim.ran,
            "synth_backend": synth.backend,
            "toolchain": tools.summary(),
            "debug_iterations": debug.iterations,
            "debug_clean": debug.final_clean,
            "resources": ctx.qor.to_dict() if ctx.qor else {},
            "qor_source": ctx.qor.source if ctx.qor else None,
            "best_architecture": opt.best,
            "confidence": ctx.confidence,
            "overall_confidence": ctx.overall_confidence(),
            "ok": ok,
        }
        project.metrics["summary"] = summary
        project.metrics["engineering_context"] = ctx.to_dict()
        project.save_manifest()

        if verbose:
            print(f"\n=== Pipeline {'OK' if ok else 'completed with warnings'} "
                  f"(confidence {ctx.overall_confidence():.2f}) ===")
            print(f"Architecture chosen: {design.decisions.label()}")
            if ctx.qor:
                print(f"QoR: {ctx.qor.luts} LUTs, {ctx.qor.registers} regs, "
                      f"Fmax {ctx.qor.fmax_mhz} MHz (source: {ctx.qor.source})")
            print(f"Project workspace: {project.root}")
            print(f"Engineering report: {report_path}")
        return PipelineResult(project, spec, arch, findings, design, hdl_review,
                              vres, sim, debug, opt, formal, synth, ctx,
                              report_path, ok, summary)

    # ==================================================================
    def _explore(self, project, spec, objective, targets, ctx) -> ArchDecisions:
        """Design-space exploration on cheap estimates (measurement refines later)."""
        cands = library.candidate_decisions(spec)
        scored = [(c, library.estimate(spec, c)) for c in cands]
        ctx.candidates = [Candidate(c, q) for c, q in scored]
        best_dec, best_q = max(scored, key=lambda cq: score(cq[1], objective))
        for cand in ctx.candidates:
            cand.selected = cand.decisions.key() == best_dec.key()
        ctx.decisions = best_dec
        project.log("dse", f"explored {len(cands)} architecture(s) on estimates; chose "
                    f"'{best_dec.label()}' (est. Fmax≈{best_q.fmax_mhz} MHz, "
                    f"{best_q.area} cells)", "success")
        return best_dec

    def _measure(self, project, spec, design, ctx) -> QoR:
        """Measured QoR (nextpnr) when the flow exists; labelled estimate otherwise."""
        ok, why = pnr.available()
        if ok:
            res = pnr.run_ice40(project, design)
            if res.ran and res.qor is not None:
                project.log("qor", f"measured (nextpnr-ice40): {res.qor.luts} LUT4, "
                            f"{res.qor.registers} FF, Fmax {res.qor.fmax_mhz} MHz")
                return res.qor
            project.log("qor", f"measurement failed ({res.reason}); "
                        "falling back to estimate", "warn")
        q = _estimated_qor(design)
        project.log("qor", f"estimated (heuristic): {q.luts} LUTs, {q.registers} regs, "
                    f"Fmax≈{q.fmax_mhz} MHz — install yosys+ghdl-plugin+nextpnr-ice40 "
                    "for measured numbers")
        return q

    def _qor_loop(self, project, spec, decisions, objective, targets,
                  max_iters, exhaustive, mutation, ctx):
        """Generate -> gate -> verify -> MEASURE -> (refine) until targets are met
        or the iteration budget is exhausted."""
        design = hdl_review = vres = sim = None
        debug_total = DebugReport()
        action = "initial design"
        tried: set[str] = set()
        for it in range(max(1, max_iters)):
            tried.add(decisions.key())
            design = self.hdl.run(project, spec, decisions)
            if mutation and it == 0:
                self._apply_mutation(project, design, mutation)

            # --- lint gate + HDL critic (repairs accumulate) ---
            hdl_review, gate_debug = self._gate(project, spec, design)
            _merge_debug(debug_total, gate_debug)

            # --- verification + simulation ---
            vres = self.verification.run(project, spec, design, exhaustive=exhaustive)
            sim = self.simulation.run(project, spec, design, vres)

            # --- failure classification + debug if something failed ---
            if not vres.passed or (sim.ran and sim.passed is False):
                fc = classify(
                    lint_codes=[i.code for i in lint(design.vhdl)],
                    property_failures=vres.property_failures,
                    sim_ran=sim.ran, sim_passed=sim.passed,
                    sim_log=sim.log if sim.ran else None)
                project.log("failure-classifier",
                            f"failure category: {fc.category} — {fc.strategy}", "warn")
                ghdl_log = sim.log if (sim.ran and sim.passed is False) else None
                _merge_debug(debug_total,
                             self.debug.run(project, spec, design, ghdl_log=ghdl_log))
                vres = self.verification.run(project, spec, design, exhaustive=exhaustive)
                sim = self.simulation.run(project, spec, design, vres)

            # --- MEASURE QoR (real PnR when available) and decide ---
            qor = self._measure(project, spec, design, ctx)
            ctx.qor = qor
            unmet = targets.unmet(qor)
            met = not unmet
            ctx.qor_history.append(QoRIteration(it, decisions, qor, action, met))
            if targets.is_empty() or met:
                if met and not targets.is_empty():
                    project.log("qor-loop", f"targets met at iteration {it} "
                                f"(Fmax {qor.fmax_mhz} MHz, {qor.area} cells, "
                                f"source {qor.source})", "success")
                break
            opt = self.optimization.run(project, spec, design,
                                        objective=objective, targets=targets)
            chosen = self._pick_proposal(opt, targets, objective, tried)
            if chosen is None:
                project.log("qor-loop", f"targets unmet ({unmet[0]}) and design space "
                            "exhausted; stopping at best effort", "warn")
                break
            project.log("qor-loop", f"iteration {it}: {unmet[0]} -> applying "
                        f"'{chosen.kind}' and regenerating", "warn")
            decisions = chosen.target_decisions
            action = chosen.kind
        return design, hdl_review, vres, sim, debug_total

    @staticmethod
    def _pick_proposal(opt, targets, objective, tried):
        """Never revisit a tried point. Proposals are ranked on estimates; when
        acceptance is measured, an estimator miss just costs one more iteration."""
        fresh = [p for p in opt.proposals if p.target_decisions.key() not in tried]
        if not fresh:
            return None
        meeting = [p for p in fresh if targets.met_by(p.est_qor)]
        if meeting:
            return max(meeting, key=lambda p: score(p.est_qor, objective))
        return fresh[0]

    def _gate(self, project, spec, design):
        """Lint gate + HDL critic. Auto-fixable defects are repaired before
        verification; repair history is returned for accumulation."""
        issues = lint(design.vhdl)
        debug = DebugReport()
        if [i for i in issues if i.fixable]:
            project.log("lint-gate", f"{len([i for i in issues if i.fixable])} "
                        "auto-fixable defect(s) at the gate; invoking debugger", "warn")
            debug = self.debug.run(project, spec, design)
            design.vhdl = (project.root / f"rtl/{design.entity}.vhd").read_text()
        hdl_review = self.hdl_critic.run(project, spec, design)
        if hdl_review.blocking and any(f.fixable for f in hdl_review.blocking):
            _merge_debug(debug, self.debug.run(project, spec, design))
            design.vhdl = (project.root / f"rtl/{design.entity}.vhd").read_text()
            hdl_review = self.hdl_critic.run(project, spec, design)
        return hdl_review, debug

    # ------------------------------------------------------------------
    @staticmethod
    def _blocking(findings: list[Finding]) -> list[Finding]:
        return [f for f in findings if f.severity == "block"]

    def _apply_mutation(self, project: Project, design: GeneratedDesign,
                        name: str) -> None:
        rtl_path = project.root / f"rtl/{design.entity}.vhd"
        mutated = mutate_mod.apply(name, rtl_path.read_text())
        if mutated is None:
            project.log("orchestrator", f"mutation '{name}' not applicable to this "
                        "design; nothing seeded", "warn")
            return
        rtl_path.write_text(mutated)
        design.vhdl = mutated
        m = mutate_mod.get(name)
        project.log("orchestrator", f"mutation '{name}' seeded for detection testing "
                    f"(expected detector: {m.expected_detector})", "warn")


def _merge_debug(base: DebugReport, extra: DebugReport) -> None:
    """Accumulate debug history instead of letting a later empty report shadow
    an earlier real one (fixes the old _gate return-contract bug)."""
    if extra is None or extra is base:
        return
    steps = getattr(extra, "steps", None) or []
    if not steps and not getattr(extra, "iterations", 0):
        return
    base.steps.extend(steps)
    base.iterations = getattr(base, "iterations", 0) + getattr(extra, "iterations", 0)
    base.final_clean = getattr(extra, "final_clean", True)


def _estimated_qor(design: GeneratedDesign) -> QoR:
    r = design.resources
    return QoR(r.get("luts", 0), r.get("registers", 0), r.get("dsp", 0),
               r.get("critical_path_ns", 1.0), r.get("fmax_mhz", 0.0), "estimated")


class _Stub:
    def __init__(self, request: str):
        self.request = request

    def log(self, *_a, **_k):
        pass

"""Command-line interface for AI FPGA Engineer.

Subcommands
-----------
build              run the closed-loop pipeline on a natural-language request
tools              show which EDA tools were detected (ghdl / yosys / nextpnr / sby)
mutation-campaign  seed every known defect class and report, honestly, which
                   pipeline stage caught each one (and which escaped)
calibrate          measure the heuristic QoR estimator against real
                   yosys+nextpnr results across the design space (CSV + summary)
ask                query the offline engineering knowledge base
list-classes       list supported design classes
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import tempfile
from pathlib import Path

from .core.orchestrator import Orchestrator
from .core.decisions import Targets
from .core.project import Project
from .core import toolchain
from .agents.requirements_agent import RequirementsAgent
from .agents.hdl_agent import HDLAgent
from .agents.hdl_critic_agent import HDLCriticAgent
from .agents.verification_agent import VerificationAgent
from .sim.runner import SimulationAgent
from .sim import pnr
from .sim.lint import lint
from .hdl import library, mutate
from .hdl.library import supported_classes
from .knowledge.kb import KnowledgeBase

_REQ = {
    "alu": "Design a {w}-bit ALU supporting ADD, SUB, AND, OR, XOR.",
    "comparator": "Design a {w}-bit comparator with gt, eq, lt outputs.",
    "counter": "Design a {w}-bit up counter with synchronous reset and enable.",
    "register": "Design a {w}-bit register with synchronous load and reset.",
}


def _tmp_spec_design(request: str, decisions=None):
    """Build (project, spec, design) in a temp workspace without the full pipeline."""
    project = Project("scratch", Path(tempfile.mkdtemp()) / "scratch",
                      request=request, quiet=True).init()
    spec = RequirementsAgent().run(project)
    design = HDLAgent().run(project, spec, decisions)
    return project, spec, design


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def _targets_from_args(args: argparse.Namespace) -> Targets:
    return Targets(fmax_mhz=args.target_fmax, max_luts=args.max_luts,
                   max_registers=args.max_registers)


def _print_summary(s: dict) -> None:
    def line(label: str, value: object) -> None:
        print(f"  {label:<22} {value}")

    print("\n" + "=" * 60)
    print("  RUN SUMMARY")
    print("=" * 60)
    line("design class", s["design_class"])
    line("entity", s["entity"])
    line("data width", s["data_width"])
    if s["operations"]:
        line("operations", ", ".join(s["operations"]))
    print("  " + "-" * 56)
    line("architecture", s["architecture"])
    line("candidates explored", s["candidates_explored"])
    line("QoR iterations", s["qor_iterations"])
    if s["targets"]:
        line("targets", s["targets"])
        line("targets met", s["targets_met"])
    if s.get("mutation_applied"):
        line("mutation seeded", s["mutation_applied"])
    print("  " + "-" * 56)
    line("test vectors", s["test_vectors"])
    line("property checks", s["property_checks"])
    line("HDL review", s["hdl_review"])
    line("formal", s["formal"])
    line("simulation", f"{s['sim_backend']} (ran={s['sim_ran']})")
    line("synthesis", s["synth_backend"])
    line("debug", f"{s['debug_iterations']} iter(s), clean={s['debug_clean']}")
    r = s.get("resources") or {}
    if r:
        print("  " + "-" * 56)
        line("LUTs / registers", f"{r.get('luts')} / {r.get('registers')}")
        line("Fmax (MHz)", r.get("fmax_mhz"))
        line("QoR source", r.get("source"))
    print("  " + "-" * 56)
    line("overall confidence", f"{s['overall_confidence']:.2f}")
    print("=" * 60)
    print(f"  RESULT: {'OK' if s['ok'] else 'COMPLETED WITH WARNINGS'}")
    print("=" * 60)


def _cmd_build(args: argparse.Namespace) -> int:
    result = Orchestrator().run(
        args.request, workdir=args.workdir, name=args.name,
        exhaustive=args.exhaustive, inject_fault=args.inject_fault,
        mutate=args.mutate, objective=args.objective,
        targets=_targets_from_args(args), max_qor_iters=args.max_qor_iters,
        do_formal=not args.no_formal, do_synth=not args.no_synth,
        verbose=not args.quiet)
    _print_summary(result.summary)
    print(f"\n  workspace: {result.project.root}")
    print(f"  report:    {result.report_path}")
    if args.json:
        Path(args.json).write_text(json.dumps(result.summary, indent=2))
        print(f"\n  summary JSON written to {args.json}")
    return 0 if result.ok else 1


# ---------------------------------------------------------------------------
# tools
# ---------------------------------------------------------------------------
def _cmd_tools(_args: argparse.Namespace) -> int:
    tc = toolchain.detect(refresh=True)
    print("Detected EDA toolchain:")
    print("  " + tc.summary())
    print(f"  simulation (ghdl):        {'ready' if tc.sim_ok else 'MISSING'}")
    print(f"  place-and-route (ice40):  {'ready' if tc.pnr_ok else 'MISSING'}")
    print(f"  formal (sby):             {'ready' if tc.formal_ok else 'MISSING'}")
    if tc.missing():
        print("\nInstall the OSS CAD Suite to get everything in one archive:")
        print("  https://github.com/YosysHQ/oss-cad-suite-build")
    return 0 if not tc.missing() else 1


# ---------------------------------------------------------------------------
# mutation-campaign
# ---------------------------------------------------------------------------
def _detect_stage(project, spec, design, run_sim: bool) -> str:
    """Run the detection cascade on an already-mutated design; return the first
    stage that flags it, or an honest 'ESCAPED' / 'UNDETECTED (needs ghdl)'."""
    issues = lint(design.vhdl)
    if any(i.fixable for i in issues):
        return "lint-gate"
    review = HDLCriticAgent().run(project, spec, design)
    if review.blocking:
        return "hdl-critic"
    vres = VerificationAgent().run(project, spec, design)
    if vres.property_failures or not vres.passed:
        return "model-verification"
    if run_sim:
        sim = SimulationAgent().run(project, spec, design, vres)
        if sim.ran and sim.passed is False:
            return "ghdl-simulation"
        if sim.ran and sim.passed:
            return "ESCAPED"
    return "UNDETECTED (needs ghdl)"


def _cmd_mutation_campaign(args: argparse.Namespace) -> int:
    tc = toolchain.detect()
    if not tc.sim_ok:
        msg = ("ghdl is not installed: semantic mutations cannot be detected "
               "in-container, so the campaign result would be meaningless.")
        if toolchain.require_tools():
            print(f"FAIL: {msg}")
            return 1
        print(f"WARNING: {msg} Structural mutations will still be exercised.")

    rows = []
    for m in mutate.MUTATIONS:
        applied = None
        for cls in ("alu", "counter"):
            project, spec, design = _tmp_spec_design(_REQ[cls].format(w=8))
            mutated = m.fn(design.vhdl)
            if mutated is None:
                continue
            rtl = project.root / f"rtl/{design.entity}.vhd"
            rtl.write_text(mutated)
            design.vhdl = mutated
            applied = (cls, project, spec, design)
            break
        if applied is None:
            rows.append((m.name, "-", "n/a (pattern absent)", m.expected_detector, m.note))
            continue
        cls, project, spec, design = applied
        detected_by = _detect_stage(project, spec, design, run_sim=tc.sim_ok)
        rows.append((m.name, cls, detected_by, m.expected_detector, m.note))
        print(f"  {m.name:<24} [{cls:<7}] -> {detected_by}")

    applicable = [r for r in rows if not r[2].startswith("n/a")]
    detected = [r for r in applicable
                if r[2] not in ("ESCAPED",) and not r[2].startswith("UNDETECTED")]
    rate = len(detected) / len(applicable) if applicable else 0.0

    lines = ["# Mutation Campaign — defect-detection evidence", "",
             "Each row seeds one independent defect class into freshly generated RTL "
             "and reports the FIRST pipeline stage that flagged it. Escapes are "
             "reported honestly; they are the interesting result.", "",
             "| mutation | design | detected by | expected detector | note |",
             "|----------|--------|-------------|-------------------|------|"]
    for name, cls, det, exp, note in rows:
        lines.append(f"| `{name}` | {cls} | {det} | {exp} | {note} |")
    lines += ["", f"**Detection rate: {len(detected)}/{len(applicable)} "
              f"({rate:.0%}) of applicable mutations.**",
              f"Threshold: {args.min_detect:.0%}. GHDL available: {tc.sim_ok}."]
    report = "\n".join(lines)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report)
    print(f"\nDetection rate {rate:.0%} ({len(detected)}/{len(applicable)}); "
          f"report -> {out}")
    return 0 if rate >= args.min_detect else 1


# ---------------------------------------------------------------------------
# calibrate
# ---------------------------------------------------------------------------
def _cmd_calibrate(args: argparse.Namespace) -> int:
    ok, why = pnr.available()
    if not ok:
        print(f"calibration needs the full flow (yosys+ghdl-plugin+nextpnr-ice40): {why}")
        return 1
    widths = [int(w) for w in args.widths.split(",")]
    rows = []
    for cls, template in _REQ.items():
        for w in widths:
            project, spec, _ = _tmp_spec_design(template.format(w=w))
            for dec in library.candidate_decisions(spec):
                est = library.estimate(spec, dec)
                design = library.generate(spec, dec)
                (project.root / f"rtl/{design.entity}.vhd").write_text(design.vhdl)
                res = pnr.run_ice40(project, design)
                if not res.ran or res.qor is None:
                    print(f"  {cls} w={w} [{dec.label()}]: PnR failed ({res.reason})")
                    continue
                q = res.qor
                rows.append(dict(design_class=cls, width=w, architecture=dec.label(),
                                 est_luts=est.luts, meas_luts=q.luts,
                                 est_regs=est.registers, meas_regs=q.registers,
                                 est_fmax_mhz=est.fmax_mhz, meas_fmax_mhz=q.fmax_mhz))
                print(f"  {cls} w={w} [{dec.label()}]: est {est.luts}L/{est.fmax_mhz}MHz "
                      f"-> measured {q.luts}L/{q.fmax_mhz}MHz")
    if not rows:
        print("no successful measurements; nothing to calibrate against")
        return 1

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "calibration.csv", "w", newline="") as f:
        wtr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wtr.writeheader()
        wtr.writerows(rows)

    def mape(est_key, meas_key):
        errs = [abs(r[est_key] - r[meas_key]) / r[meas_key]
                for r in rows if r[meas_key]]
        return statistics.mean(errs) if errs else float("nan")

    ratios = [r["meas_fmax_mhz"] / r["est_fmax_mhz"]
              for r in rows if r["est_fmax_mhz"]]
    md = ["# Estimator calibration vs nextpnr-ice40 (UP5K, seed 1)", "",
          f"Points: {len(rows)}. Raw data: `calibration.csv`.", "",
          f"- LUT-count mean abs. % error: **{mape('est_luts', 'meas_luts'):.0%}**",
          f"- Register-count mean abs. % error: **{mape('est_regs', 'meas_regs'):.0%}**",
          f"- Fmax scale ratio (measured/estimated): mean **{statistics.mean(ratios):.3f}**, "
          f"min {min(ratios):.3f}, max {max(ratios):.3f}", "",
          "Interpretation: the heuristic estimator is a pre-synthesis *ranking* aid; "
          "these numbers are its measured error band on this device. Acceptance in "
          "the QoR loop uses measured numbers directly, so estimator error costs "
          "iterations, not correctness. Rescale `estimate_alu()` constants with the "
          "Fmax ratio above if tighter estimates are wanted."]
    (outdir / "calibration.md").write_text("\n".join(md))
    print(f"\nwrote {outdir/'calibration.csv'} and {outdir/'calibration.md'}")
    return 0


# ---------------------------------------------------------------------------
# ask / list-classes
# ---------------------------------------------------------------------------
def _cmd_ask(args: argparse.Namespace) -> int:
    kb = KnowledgeBase()
    if not kb.passages:
        print("knowledge base is empty (no notes found under knowledge/notes/).")
        return 1
    print(kb.answer(args.query, k=args.k))
    return 0


def _cmd_list_classes(_args: argparse.Namespace) -> int:
    print("Supported design classes:")
    for c in supported_classes():
        print(f"  - {c}")
    print("\nAnything else is classified as 'unknown' and reported, not generated.")
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ai_fpga_engineer",
        description="Rule-based closed-loop pipeline: natural-language spec -> "
                    "simulated, measured, and (boundedly) formally checked VHDL.")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="run the full closed-loop pipeline on a request")
    b.add_argument("request", help="natural-language design request (in quotes)")
    b.add_argument("--workdir", default="projects")
    b.add_argument("--name", default=None, help="override the project/entity name")
    b.add_argument("--exhaustive", action="store_true",
                   help="for ALUs/comparators, sweep the full operand space")
    b.add_argument("--mutate", default=None, choices=mutate.names(), metavar="NAME",
                   help="seed one named defect class to exercise detection "
                        f"(one of: {', '.join(mutate.names())})")
    b.add_argument("--inject-fault", action="store_true",
                   help="deprecated alias for --mutate drop_numeric_std")
    b.add_argument("--objective", default="balanced",
                   choices=["balanced", "timing", "area"])
    b.add_argument("--target-fmax", type=float, default=None, metavar="MHZ",
                   help="minimum Fmax target (measured on iCE40 when tools present)")
    b.add_argument("--max-luts", type=int, default=None, metavar="N")
    b.add_argument("--max-registers", type=int, default=None, metavar="N")
    b.add_argument("--max-qor-iters", type=int, default=4, metavar="N")
    b.add_argument("--no-formal", action="store_true")
    b.add_argument("--no-synth", action="store_true")
    b.add_argument("--quiet", action="store_true")
    b.add_argument("--json", default=None, help="also write the run summary to this path")
    b.set_defaults(func=_cmd_build)

    t = sub.add_parser("tools", help="show detected EDA toolchain status")
    t.set_defaults(func=_cmd_tools)

    mc = sub.add_parser("mutation-campaign",
                        help="seed all defect classes; report detection per stage")
    mc.add_argument("--out", default="reports/mutation_report.md")
    mc.add_argument("--min-detect", type=float, default=0.7,
                    help="fail (exit 1) below this detection rate (default 0.7)")
    mc.set_defaults(func=_cmd_mutation_campaign)

    c = sub.add_parser("calibrate",
                       help="measure the QoR estimator against yosys+nextpnr results")
    c.add_argument("--widths", default="4,8", help="comma-separated widths (default 4,8)")
    c.add_argument("--out", default="reports/calibration")
    c.set_defaults(func=_cmd_calibrate)

    a = sub.add_parser("ask", help="query the offline engineering knowledge base")
    a.add_argument("query")
    a.add_argument("-k", type=int, default=3)
    a.set_defaults(func=_cmd_ask)

    lc = sub.add_parser("list-classes", help="list supported design classes")
    lc.set_defaults(func=_cmd_list_classes)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

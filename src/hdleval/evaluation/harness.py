from __future__ import annotations

import time
import uuid
from pathlib import Path

from ..benchmarks.loader import reference_hdl, testbench_hdl
from ..benchmarks.schema import Benchmark
from ..config.schema import ExperimentConfig, ModelConfig, PromptConfig
from ..logging.structured import StageEvent, StructuredLogger
from ..metrics.resources import resource_metrics
from ..metrics.static_analysis import analyze_vhdl
from ..models.base import ModelProvider, ModelRequest, derive_run_seed
from ..parsing.hdl_extract import extract_vhdl
from ..parsing.ports import PortSig, compare_interfaces, entity_declaration, parse_ports
from ..prompts.templates import build_prompt, build_repair_prompt
from ..registry.experiment import ExperimentRecord
from ..registry.pricing import compute_cost_usd
from ..toolchain import compile_vhdl, detect, simulate, synthesize
from ..toolchain.detect import ToolchainMissingError, missing_tools, require_tools
from ..toolchain.nextpnr import place_and_route
from ..verification.equivalence import EquivResult, check_equivalence
from ..verification.error_kinds import classify_tool_error
from ..verification.failures import FailureClass, classify_failure
from ..verification.properties import run_lint
from .result import BenchmarkResult, StageOutcome


class EvaluationHarness:
    def __init__(
        self,
        experiment: ExperimentConfig,
        *,
        logger: StructuredLogger | None = None,
        benchmarks_root: str | Path | None = None,
    ) -> None:
        self.experiment = experiment
        self.logger = logger or StructuredLogger()
        self.benchmarks_root = benchmarks_root
        self.toolchain = detect()
        if require_tools():
            missing = missing_tools(
                self.toolchain,
                place_and_route=experiment.synthesis.place_and_route,
                equivalence=experiment.verification.equivalence,
            )
            if missing:
                raise ToolchainMissingError(
                    "HDLEVAL_REQUIRE_TOOLS=1 but missing: "
                    + ", ".join(missing)
                    + ". Install them (see Dockerfile) or unset the variable for a "
                    "degraded, non-publishable run."
                )

    def evaluate(
        self,
        benchmark: Benchmark,
        provider: ModelProvider,
        model_cfg: ModelConfig,
        prompt_cfg: PromptConfig,
        trial: int,
        run_id: str | None = None,
    ) -> tuple[BenchmarkResult, ExperimentRecord]:
        run_id = run_id or uuid.uuid4().hex[:12]
        run_seed = derive_run_seed(self.experiment.seed, model_cfg.name, benchmark.id, trial)
        result = BenchmarkResult(
            benchmark=benchmark.id,
            category=benchmark.category,
            difficulty=benchmark.estimated_difficulty,
            model=model_cfg.name,
            prompt=prompt_cfg.name,
            trial=trial,
        )
        rec = ExperimentRecord(
            experiment=self.experiment.name,
            run_id=run_id,
            benchmark=benchmark.id,
            benchmark_version=benchmark.version,
            model=model_cfg.name,
            model_id=model_cfg.model_id,
            prompt=prompt_cfg.name,
            seed=self.experiment.seed,
            trial=trial,
            inference_config={
                "temperature": model_cfg.temperature,
                "top_p": model_cfg.top_p,
                "max_tokens": model_cfg.max_tokens,
                "seed": model_cfg.seed,
                "run_seed": run_seed,
            },
            toolchain={"summary": self.toolchain.summary()},
        )
        t_start = time.perf_counter()
        ref = reference_hdl(benchmark, self.benchmarks_root)

        spec = with_interface(benchmark.specification, ref, benchmark.entity)
        expected_ports = expected_interface(benchmark, ref)
        system, user = build_prompt(prompt_cfg, spec)
        hdl, resp = self._infer(provider, model_cfg, system, user, benchmark, ref, trial, run_seed)
        input_tokens = resp.prompt_tokens
        output_tokens = resp.completion_tokens
        result.metrics["inference_latency_s"] = resp.latency_s
        if "fault" in resp.raw:
            result.metrics["injected_fault"] = resp.raw["fault"]
        self._emit(
            run_id,
            benchmark.id,
            "inference",
            "ok" if resp.finish_reason != "no_reference" else "fail",
            resp.latency_s,
            {"tokens": resp.total_tokens},
        )

        parsed = extract_vhdl(hdl)
        result.hdl = parsed.code
        self._stage(
            result,
            "parse",
            "ok" if parsed.found else "fail",
            detail={"entity": parsed.entity, "n_blocks": parsed.n_blocks},
        )

        retries = 0
        compile_res = compile_vhdl(parsed.code, entity=parsed.entity or benchmark.entity)
        while (
            compile_res.status == "fail"
            and retries < prompt_cfg.max_repair_iterations
            and parsed.found
        ):
            retries += 1
            diag = f"Compilation failed:\n{compile_res.stderr[:800]}"
            rsys, ruser = build_repair_prompt(prompt_cfg, spec, parsed.code, diag)
            hdl, resp = self._infer(
                provider, model_cfg, rsys, ruser, benchmark, ref, trial, run_seed
            )
            input_tokens += resp.prompt_tokens
            output_tokens += resp.completion_tokens
            parsed = extract_vhdl(hdl)
            result.hdl = parsed.code
            compile_res = compile_vhdl(parsed.code, entity=parsed.entity or benchmark.entity)
            rec.retry_history.append({"iteration": retries, "status": compile_res.status})
        result.retries = retries
        rec.retry_history = rec.retry_history

        self._stage(
            result, "compile", compile_res.status, detail={"stderr": compile_res.stderr[:400]}
        )

        iface_problems: list[str] = []
        if parsed.found and expected_ports:
            if (parsed.entity or "").lower() != benchmark.entity.lower():
                iface_problems.append(
                    f"entity named {parsed.entity!r}, expected {benchmark.entity!r}"
                )
            else:
                iface_problems = compare_interfaces(
                    expected_ports, parse_ports(parsed.code, benchmark.entity)
                )
        iface_status = (
            "skipped"
            if not (parsed.found and expected_ports)
            else ("fail" if iface_problems else "ok")
        )
        self._stage(result, "interface", iface_status, detail={"problems": iface_problems})

        synth = (
            synthesize(
                parsed.code,
                parsed.entity or benchmark.entity,
                target=self.experiment.synthesis.target,
            )
            if (parsed.found and self.experiment.synthesis.enabled)
            else _skipped()
        )
        self._stage(result, "synthesis", synth.status, detail=synth.metrics)
        pnr = (
            place_and_route(parsed.code, parsed.entity or benchmark.entity)
            if synth.ok and self.experiment.synthesis.place_and_route
            else _skipped()
        )
        self._stage(
            result, "place_and_route", pnr.status, detail={**pnr.metrics, "err": pnr.stderr[:200]}
        )
        rmetrics = resource_metrics(synth, pnr)
        result.metrics["resources"] = rmetrics.to_dict()

        tb = testbench_hdl(benchmark, self.benchmarks_root)
        if parsed.found and tb and benchmark.testbench_entity:
            sim = simulate(parsed.code, tb, benchmark.testbench_entity)
        else:
            sim = _skipped()
        self._stage(result, "simulation", sim.status, detail={"stderr": sim.stderr[:400]})

        vcfg = self.experiment.verification
        if (
            vcfg.equivalence
            and parsed.found
            and compile_res.status == "ok"
            and iface_status != "fail"
            and sim.status != "fail"
            and ref
        ):
            equiv = check_equivalence(
                parsed.code,
                ref,
                benchmark.entity,
                sequential_depth=vcfg.equivalence_depth,
                prove_timeout_s=vcfg.prove_timeout_s,
            )
        else:
            equiv = EquivResult("skipped")
        result.metrics["equivalence"] = {"status": equiv.status, "depth": equiv.depth}
        self._stage(
            result,
            "equivalence",
            "ok" if equiv.ok else ("skipped" if equiv.status == "skipped" else equiv.status),
            detail={"status": equiv.status, "depth": equiv.depth, "detail": equiv.detail},
        )

        static = analyze_vhdl(parsed.code)
        result.metrics["static"] = static.to_dict()
        lint = run_lint(parsed.code, benchmark.properties or None)
        result.metrics["lint"] = lint.results
        result.metrics["static_pass"] = bool(
            parsed.found
            and parsed.entity
            and "architecture" in parsed.code.lower()
            and lint.n_fail == 0)
        self._stage(result, "lint", "ok" if lint.n_fail == 0 else "warn", detail=lint.results)
        functional_ok = sim.status == "ok" or equiv.ok
        result.metrics["simulated"] = sim.status in ("ok", "fail")

        failure = classify_failure(
            code_found=parsed.found,
            compile_status=compile_res.status,
            synth_status=synth.status,
            sim_status=sim.status,
            functional_ok=functional_ok,
            interface_ok=iface_status != "fail",
            equiv_status=equiv.status,
        )
        result.failure_class = failure.value
        stage_output = {
            FailureClass.COMPILE: ("compile", compile_res.stderr),
            FailureClass.SYNTHESIS: ("synthesis", synth.stderr),
            FailureClass.SIMULATION: ("simulation", sim.stdout + sim.stderr),
        }.get(failure)
        if stage_output is not None:
            result.metrics["error_kind"] = classify_tool_error(stage_output[1], stage_output[0])
        result.passed = failure.value == "none"

        duration = time.perf_counter() - t_start
        rec.duration_s = round(duration, 4)
        rec.failure_class = result.failure_class
        rec.passed = result.passed
        rec.artifacts = {"hdl_chars": str(len(result.hdl))}
        rec.input_tokens = input_tokens
        rec.output_tokens = output_tokens
        rec.cost_usd = compute_cost_usd(model_cfg.model_id, input_tokens, output_tokens)
        result.metrics["prompt_tokens"] = input_tokens
        result.metrics["completion_tokens"] = output_tokens
        result.metrics["cost_usd"] = rec.cost_usd
        rec.metrics = result.metrics
        return result, rec

    def _infer(self, provider, model_cfg, system, user, benchmark, ref, trial=0, run_seed=0):
        req = ModelRequest(
            system=system,
            prompt=user,
            config=model_cfg,
            trial=trial,
            run_seed=run_seed,
            context={
                "reference_hdl": ref,
                "entity": benchmark.entity,
                "difficulty": benchmark.estimated_difficulty,
                "specification": benchmark.specification,
                "category": benchmark.category,
            },
        )
        resp = provider.generate(req)
        return resp.text, resp

    def _stage(
        self,
        result: BenchmarkResult,
        name: str,
        status: str,
        duration: float = 0.0,
        detail: dict | None = None,
    ) -> None:
        result.stages.append(StageOutcome(name, status, duration, detail or {}))
        self._emit(None, result.benchmark, name, status, duration, detail or {})

    def _emit(self, run_id, benchmark, stage, status, duration, detail):
        self.logger.log(
            StageEvent(
                experiment=self.experiment.name,
                run_id=run_id or "",
                benchmark=benchmark,
                stage=stage,
                status=status,
                duration_s=duration,
                detail=detail or {},
            )
        )

def with_interface(specification: str, reference: str, entity: str) -> str:
    """Append the reference's entity declaration to the natural-language spec."""
    decl = entity_declaration(reference, entity)
    if not decl:
        return specification
    return (
        f"{specification}\n\nImplement exactly this entity declaration "
        f"(same entity name, port names, directions and widths):\n```vhdl\n{decl}\n```"
    )


def expected_interface(benchmark: Benchmark, reference: str) -> list[PortSig]:
    """Declared interfaces if the benchmark lists them, else the reference's ports."""
    if benchmark.interfaces:
        return [
            PortSig(p.name.lower(), p.direction, p.width, "", p.width > 1)
            for p in benchmark.interfaces
        ]
    return parse_ports(reference, benchmark.entity) or []

def _skipped():
    from ..toolchain.detect import ToolResult

    return ToolResult(status="skipped")

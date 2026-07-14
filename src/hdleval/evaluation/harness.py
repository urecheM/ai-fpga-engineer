"""The evaluation harness.

Every benchmark, for every model, goes through one identical procedure:

    load spec -> build prompt -> infer -> parse -> compile -> synthesize
    -> simulate -> compute metrics -> check properties -> classify -> record

Model inference is injected as a :class:`ModelProvider`, so adding a model never
touches evaluation logic. Toolchain stages degrade to ``skipped`` when the tool
is absent, so the harness runs anywhere while remaining strict in CI.
"""

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
from ..models.base import ModelProvider, ModelRequest
from ..parsing.hdl_extract import extract_vhdl
from ..prompts.templates import build_prompt, build_repair_prompt
from ..registry.experiment import ExperimentRecord
from ..toolchain import compile_vhdl, detect, simulate, synthesize
from ..verification.failures import classify_failure
from ..verification.properties import check_properties
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

    # -- one benchmark x model x prompt x trial -----------------------------
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
            },
            toolchain={"summary": self.toolchain.summary()},
        )
        t_start = time.perf_counter()
        ref = reference_hdl(benchmark, self.benchmarks_root)

        # ---- inference ----
        spec = benchmark.specification
        system, user = build_prompt(prompt_cfg, spec)
        hdl, resp = self._infer(provider, model_cfg, system, user, benchmark, ref)
        result.metrics["inference_latency_s"] = resp.latency_s
        result.metrics["prompt_tokens"] = resp.prompt_tokens
        result.metrics["completion_tokens"] = resp.completion_tokens
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

        # ---- self-repair loop (optional) ----
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
            hdl, resp = self._infer(provider, model_cfg, rsys, ruser, benchmark, ref)
            parsed = extract_vhdl(hdl)
            result.hdl = parsed.code
            compile_res = compile_vhdl(parsed.code, entity=parsed.entity or benchmark.entity)
            rec.retry_history.append({"iteration": retries, "status": compile_res.status})
        result.retries = retries
        rec.retry_history = rec.retry_history

        self._stage(
            result, "compile", compile_res.status, detail={"stderr": compile_res.stderr[:400]}
        )

        # ---- synthesis ----
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
        rmetrics = resource_metrics(synth, clock_ns=self.experiment.synthesis.clock_ns)
        result.metrics["resources"] = rmetrics.to_dict()

        # ---- simulation (reference vectors) ----
        tb = testbench_hdl(benchmark, self.benchmarks_root)
        if parsed.found and tb and benchmark.testbench_entity:
            sim = simulate(parsed.code, tb, benchmark.testbench_entity)
        else:
            sim = _skipped()
        self._stage(result, "simulation", sim.status, detail={"stderr": sim.stderr[:400]})

        # ---- static analysis + properties ----
        static = analyze_vhdl(parsed.code)
        result.metrics["static"] = static.to_dict()
        props = check_properties(parsed.code, benchmark.properties or None)
        result.metrics["properties"] = props.results
        self._stage(
            result, "properties", "ok" if props.n_fail == 0 else "fail", detail=props.results
        )

        # ---- functional determination ----
        # With tools present, functional_ok requires a passing simulation.
        # Without a simulator, we fall back to a successful compile + no failed
        # properties (a weaker, clearly-labelled signal).
        if sim.status == "ok":
            functional_ok = True
        elif sim.status == "skipped":
            functional_ok = compile_res.status in ("ok", "skipped") and props.n_fail == 0
        else:
            functional_ok = False

        failure = classify_failure(
            code_found=parsed.found,
            compile_status=compile_res.status,
            synth_status=synth.status,
            sim_status=sim.status,
            functional_ok=functional_ok,
            property_fail=props.n_fail > 0,
        )
        result.failure_class = failure.value
        result.passed = failure.value == "none"

        duration = time.perf_counter() - t_start
        rec.duration_s = round(duration, 4)
        rec.metrics = result.metrics
        rec.failure_class = result.failure_class
        rec.passed = result.passed
        rec.artifacts = {"hdl_chars": str(len(result.hdl))}
        return result, rec

    # -- helpers ------------------------------------------------------------
    def _infer(self, provider, model_cfg, system, user, benchmark, ref):
        req = ModelRequest(
            system=system,
            prompt=user,
            config=model_cfg,
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


def _skipped():
    from ..toolchain.detect import ToolResult

    return ToolResult(status="skipped")

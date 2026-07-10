"""Load YAML config files into typed dataclasses.

The loader keeps a strict separation between *reference by name* (e.g. an
experiment names ``models: [claude-sonnet, reference-golden]``) and the
concrete config files under ``configs/``. This lets experiments compose
reusable building blocks.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .schema import (
    BenchmarkSelector,
    ConfigError,
    ExperimentConfig,
    ModelConfig,
    OptimizationConfig,
    PromptConfig,
    SynthesisConfig,
    VerificationConfig,
)


def resolve_config_dir(explicit: str | os.PathLike[str] | None = None) -> Path:
    """Return the ``configs/`` directory (env override: ``HDLEVAL_CONFIG_DIR``)."""
    if explicit is not None:
        return Path(explicit)
    env = os.environ.get("HDLEVAL_CONFIG_DIR")
    if env:
        return Path(env)
    # repo-root/configs, computed relative to this file (src/hdleval/config/loader.py)
    return Path(__file__).resolve().parents[3] / "configs"


def load_yaml(path: str | os.PathLike[str]) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"config file not found: {p}")
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ConfigError(f"config {p} must be a mapping, got {type(data).__name__}")
    return data


def _load_named(kind: str, name: str, cfg_dir: Path) -> dict[str, Any]:
    path = cfg_dir / kind / f"{name}.yaml"
    return load_yaml(path)


def load_model(name: str, cfg_dir: Path) -> ModelConfig:
    d = _load_named("models", name, cfg_dir)
    return ModelConfig(
        name=d.get("name", name),
        provider=d["provider"],
        model_id=d.get("model_id", ""),
        temperature=float(d.get("temperature", 0.0)),
        max_tokens=int(d.get("max_tokens", 4096)),
        top_p=float(d.get("top_p", 1.0)),
        seed=d.get("seed", 0),
        system_prompt=d.get("system_prompt", ""),
        extra=d.get("extra", {}),
    )


def load_prompt(name: str, cfg_dir: Path) -> PromptConfig:
    d = _load_named("prompts", name, cfg_dir)
    return PromptConfig(
        name=d.get("name", name),
        strategy=d.get("strategy", "direct"),
        system=d.get("system", ""),
        template=d.get("template", "{specification}"),
        few_shot_examples=d.get("few_shot_examples", []),
        max_repair_iterations=int(d.get("max_repair_iterations", 0)),
    )


def _selector(d: dict[str, Any]) -> BenchmarkSelector:
    return BenchmarkSelector(
        suite_version=d.get("suite_version", "v1"),
        categories=d.get("categories", []),
        difficulty_min=int(d.get("difficulty_min", 0)),
        difficulty_max=int(d.get("difficulty_max", 100)),
        ids=d.get("ids", []),
    )


def _named_or_inline(
    kind: str, spec: Any, cfg_dir: Path, ctor: Any
) -> Any:
    """Accept either a string (name -> file) or an inline mapping."""
    if isinstance(spec, str):
        return ctor(**_load_named(kind, spec, cfg_dir))
    if isinstance(spec, dict):
        return ctor(**spec)
    raise ConfigError(f"{kind} must be a name or mapping, got {type(spec).__name__}")


def load_experiment(
    path: str | os.PathLike[str], cfg_dir: str | os.PathLike[str] | None = None
) -> ExperimentConfig:
    """Load an experiment YAML, resolving named references into typed configs."""
    d = load_yaml(path)
    cdir = resolve_config_dir(cfg_dir)

    models = [load_model(m, cdir) if isinstance(m, str) else ModelConfig(**m)
              for m in d.get("models", [])]
    prompts = [load_prompt(p, cdir) if isinstance(p, str) else PromptConfig(**p)
               for p in d.get("prompts", [])]

    synth = _named_or_inline("synthesis", d["synthesis"], cdir, SynthesisConfig) \
        if "synthesis" in d else SynthesisConfig()
    verif = _named_or_inline("verification", d["verification"], cdir, VerificationConfig) \
        if "verification" in d else VerificationConfig()
    opt = _named_or_inline("optimization", d["optimization"], cdir, OptimizationConfig) \
        if "optimization" in d else OptimizationConfig()

    exp = ExperimentConfig(
        name=d["name"],
        description=d.get("description", ""),
        models=models,
        prompts=prompts,
        benchmarks=_selector(d.get("benchmarks", {})),
        synthesis=synth,
        verification=verif,
        optimization=opt,
        trials=int(d.get("trials", 1)),
        seed=int(d.get("seed", 0)),
        tags=d.get("tags", []),
    )
    exp.validate()
    return exp

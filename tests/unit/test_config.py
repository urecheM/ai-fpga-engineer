from __future__ import annotations

import pytest

from hdleval.config.loader import load_experiment, resolve_config_dir
from hdleval.config.schema import ConfigError, ExperimentConfig, ModelConfig, PromptConfig


def test_model_config_validation():
    ModelConfig(name="m", provider="reference").validate()
    with pytest.raises(ConfigError):
        ModelConfig(name="m", provider="bogus").validate()
    with pytest.raises(ConfigError):
        ModelConfig(name="m", provider="reference", temperature=5.0).validate()


def test_prompt_requires_specification():
    with pytest.raises(ConfigError):
        PromptConfig(name="p", template="no placeholder").validate()
    PromptConfig(name="p", template="{specification}").validate()


def test_experiment_requires_models_and_prompts():
    with pytest.raises(ConfigError):
        ExperimentConfig(name="x").validate()


def test_load_baseline_experiment(repo_root):
    exp = load_experiment(repo_root / "configs/experiments/baseline.yaml")
    assert exp.name == "baseline-v1"
    assert len(exp.models) == 4
    assert exp.trials == 3
    exp.validate()


def test_resolve_config_dir(repo_root):
    assert resolve_config_dir().name == "configs"

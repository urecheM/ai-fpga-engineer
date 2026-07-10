from __future__ import annotations

import pytest

from hdleval.config.loader import load_yaml
from hdleval.config.schema import ConfigError


def test_load_yaml_missing(tmp_path):
    with pytest.raises(ConfigError):
        load_yaml(tmp_path / "nope.yaml")


def test_load_yaml_not_mapping(tmp_path):
    p = tmp_path / "list.yaml"
    p.write_text("- a\n- b\n")
    with pytest.raises(ConfigError):
        load_yaml(p)


def test_load_named_synthesis(repo_root):
    from hdleval.config.loader import load_experiment
    exp = load_experiment(repo_root / "configs/experiments/prompt-ablation.yaml")
    assert exp.synthesis.name == "yosys-ice40"
    assert exp.verification.strategy == "properties"

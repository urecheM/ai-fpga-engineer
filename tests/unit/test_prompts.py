from __future__ import annotations

from hdleval.config.schema import PromptConfig
from hdleval.prompts.templates import build_prompt, build_repair_prompt


def test_direct_prompt():
    sys, user = build_prompt(PromptConfig(name="d", template="Spec: {specification}"), "an adder")
    assert "an adder" in user and "code block" in user and sys


def test_chain_of_thought_suffix():
    _, user = build_prompt(
        PromptConfig(name="c", strategy="chain_of_thought", template="{specification}"), "x"
    )
    assert "step by step" in user.lower()


def test_few_shot():
    p = PromptConfig(
        name="f",
        strategy="few_shot",
        template="{specification}",
        few_shot_examples=[{"specification": "s1", "hdl": "h1"}],
    )
    _, user = build_prompt(p, "target")
    assert "s1" in user and "h1" in user and "target" in user


def test_rag_context():
    _, user = build_prompt(
        PromptConfig(name="r", strategy="rag", template="{specification}"),
        "x",
        rag_context="datasheet text",
    )
    assert "datasheet text" in user


def test_repair_prompt():
    sys, user = build_repair_prompt(
        PromptConfig(name="d", template="{specification}"), "spec", "old vhdl", "it broke"
    )
    assert "old vhdl" in user and "it broke" in user and sys

"""Render prompt strategies into concrete (system, user) message pairs.

Supported strategies mirror :class:`PromptConfig.strategy`: ``direct``,
``chain_of_thought``, ``few_shot``, ``critique`` and ``rag``. All strategies
share the same template contract so the evaluation harness is strategy-agnostic.
"""

from __future__ import annotations

from ..config.schema import PromptConfig

_COT_SUFFIX = (
    "\n\nThink step by step about the interface, state, and timing before writing "
    "the entity and architecture. Then output a single synthesizable VHDL-2008 "
    "code block."
)

_FORMAT_RULES = (
    "Output exactly one ```vhdl code block containing a complete, synthesizable "
    "VHDL-2008 design. Do not include a testbench."
)


def build_prompt(
    prompt_cfg: PromptConfig, specification: str, *, rag_context: str = ""
) -> tuple[str, str]:
    """Return ``(system, user)`` messages for the given strategy."""
    system = prompt_cfg.system or (
        "You are an expert digital design engineer. You write correct, "
        "synthesizable VHDL-2008 from natural-language specifications."
    )
    body = prompt_cfg.template.format(specification=specification)

    if prompt_cfg.strategy == "few_shot" and prompt_cfg.few_shot_examples:
        shots = "\n\n".join(
            f"Specification:\n{ex['specification']}\n\nVHDL:\n```vhdl\n{ex['hdl']}\n```"
            for ex in prompt_cfg.few_shot_examples
        )
        body = f"{shots}\n\nSpecification:\n{specification}\n\nVHDL:"
    elif prompt_cfg.strategy == "chain_of_thought":
        body = body + _COT_SUFFIX
    elif prompt_cfg.strategy == "rag" and rag_context:
        body = f"Reference material:\n{rag_context}\n\n{body}"

    user = f"{body}\n\n{_FORMAT_RULES}"
    return system, user


def build_repair_prompt(
    prompt_cfg: PromptConfig, specification: str, previous_hdl: str, diagnosis: str
) -> tuple[str, str]:
    """Construct a corrective prompt for the self-repair loop."""
    system = prompt_cfg.system or (
        "You are an expert digital design engineer fixing a failing VHDL design."
    )
    user = (
        f"The following VHDL was generated for this specification but failed "
        f"evaluation.\n\nSpecification:\n{specification}\n\n"
        f"Previous VHDL:\n```vhdl\n{previous_hdl}\n```\n\n"
        f"Diagnosis of the failure:\n{diagnosis}\n\n"
        f"Produce a corrected design. {_FORMAT_RULES}"
    )
    return system, user

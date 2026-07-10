# Experiment documentation

## Authoring an experiment
An experiment is `configs/experiments/<name>.yaml`: a cartesian product of
`models × prompts × benchmark-selector`, plus toolchain/verification/optimization
choices, `trials` and a `seed`.

## Shipped experiments
- **baseline-v1** — reference vs three synthetic-fidelity baselines over the full
  suite, 3 trials. Establishes the measurement machinery.
- **model-comparison-v1** — a real model (Anthropic) vs a synthetic baseline
  through the identical harness (requires `ANTHROPIC_API_KEY`).
- **prompt-ablation-v1** — direct vs chain-of-thought vs self-repair on a fixed
  model.

## Running
```bash
hdleval run configs/experiments/baseline.yaml --out results --db experiments/registry.sqlite
hdleval report baseline-v1 --out results         # regenerate from the registry
```

## Real-model runs (Anthropic) and the rule-based baseline

Two providers were added so the platform compares a real LLM and the mature
rule-based pipeline through the identical harness:

- `rule-based` (`configs/models/rule-based.yaml`) drives the bundled
  `ai_fpga_engineer` pipeline. Deterministic, no key. Verified-by-construction
  on the four supported classes (alu/counter/register/comparator) and no code
  elsewhere — an honest coverage/quality baseline.
- `claude-sonnet` (`configs/models/claude-sonnet.yaml`) is the real Anthropic
  provider. Set `ANTHROPIC_API_KEY` and `pip install 'hdleval[anthropic]'`;
  responses are cached to `.hdleval_cache/` for reproducibility. Without the key
  the CLI prints a preflight warning and records that model's benchmarks as
  `no_code_generated` (the run does not crash).

```bash
export ANTHROPIC_API_KEY=sk-...
hdleval run configs/experiments/model-comparison.yaml       # claude-sonnet vs rule-based vs synthetic
hdleval run configs/experiments/rule-based-vs-baselines.yaml # rule-based coverage story (no key needed)
```

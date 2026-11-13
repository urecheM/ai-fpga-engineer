# Experiment documentation
Experiment `configs/experiments/<name>.yaml` is a cartesian product of
`models × prompts × benchmark-selector` plus toolchain/verification/optimization
choices, `trials` and a `seed`.

## Shipped experiments
- baseline-v1: reference vs three synthetic-fidelity baselines over the full suite, 3 trials. Establishes the measurement machinery.
- prompt-ablation-v1: direct vs chain-of-thought vs self-repair on a fixed model.

## Running
```bash
hdleval run configs/experiments/baseline.yaml --out results --db experiments/registry.sqlite
hdleval report baseline-v1 --out results
```


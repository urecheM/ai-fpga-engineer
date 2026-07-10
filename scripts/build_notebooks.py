"""Generate Colab/Kaggle notebooks (.ipynb) for onboarding and reproduction.

Notebooks are build products so they stay in sync with the platform API.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "notebooks"


def nb(cells):
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10"},
            "colab": {"provenance": []},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": text.splitlines(keepends=True)}


CLONE = """# Setup: clone the repository and install
!git clone https://github.com/your-org/hdleval.git
%cd hdleval
!pip install -e . -q
import sys; sys.path.insert(0, 'src')"""


def onboarding():
    return nb([
        md("# hdleval — Project Onboarding\n\nAn extensible, reproducible platform "
           "for evaluating LLM-assisted hardware design. This notebook orients you "
           "in the architecture and runs a tiny experiment."),
        code(CLONE),
        md("## Inspect the versioned benchmark suite"),
        code("!hdleval list-benchmarks"),
        md("## The layered architecture\n\nInference is a `ModelProvider`; the harness "
           "never changes when you add a model."),
        code("from hdleval.models import available_providers\n"
             "print(available_providers())"),
        md("## Next\n- `02_benchmark_execution.ipynb` — run the suite\n"
           "- `03_evaluation_harness.ipynb` — the pipeline in detail\n"
           "- `04_reproduce.ipynb` — regenerate every artifact\n"
           "- `05_visualization.ipynb` — figures and leaderboards"),
    ])


def benchmark_execution():
    return nb([
        md("# hdleval — Benchmark Execution"),
        code(CLONE),
        code("from hdleval.benchmarks.loader import load_suite\n"
             "suite = load_suite('v1')\n"
             "for b in suite[:6]:\n"
             "    print(b.id, b.category, b.estimated_difficulty, '-', b.title)"),
        md("## Run a small experiment (arithmetic only)"),
        code("!hdleval run configs/experiments/baseline.yaml --out results --db experiments/registry.sqlite | tail -3"),
        code("import json\n"
             "lb = json.load(open('results/leaderboards/baseline-v1_leaderboard.json'))\n"
             "for r in lb['overall']:\n"
             "    print(r['model'], r['pass_rate'], r['pass_ci95'])"),
    ])


def evaluation_harness():
    return nb([
        md("# hdleval — Evaluation Harness Demonstration\n\nOne identical procedure "
           "per model: parse → compile → synthesize → simulate → metrics → classify."),
        code(CLONE),
        code("from hdleval.config.schema import ExperimentConfig, ModelConfig, PromptConfig\n"
             "from hdleval.evaluation.harness import EvaluationHarness\n"
             "from hdleval.models.reference import ReferenceProvider\n"
             "from hdleval.benchmarks.loader import load_suite\n\n"
             "exp = ExperimentConfig(name='demo',\n"
             "    models=[ModelConfig(name='reference-golden', provider='reference')],\n"
             "    prompts=[PromptConfig(name='direct', template='{specification}')])\n"
             "bench = next(b for b in load_suite('v1') if b.id=='fsm_traffic')\n"
             "h = EvaluationHarness(exp)\n"
             "res, rec = h.evaluate(bench, ReferenceProvider(), exp.models[0], exp.prompts[0], 0)\n"
             "print('passed:', res.passed)\n"
             "for s in res.stages: print(' ', s.stage, s.status)\n"
             "print('static metrics:', res.metrics['static'])"),
    ])


def reproduce():
    return nb([
        md("# hdleval — Experiment Reproduction\n\nOne command regenerates every "
           "figure, table, report and publication artifact."),
        code(CLONE),
        code("!python reproduce.py 2>&1 | tail -8"),
        code("from IPython.display import SVG, display\n"
             "display(SVG(filename='results/figures/pass_rate_by_model.svg'))"),
    ])


def visualization():
    return nb([
        md("# hdleval — Visualization Tutorial"),
        code(CLONE),
        code("!python reproduce.py 2>&1 | tail -2"),
        code("import json\n"
             "lb = json.load(open('results/leaderboards/baseline-v1_leaderboard.json'))\n"
             "import matplotlib.pyplot as plt\n"
             "rows = lb['overall']\n"
             "plt.bar([r['model'] for r in rows], [r['pass_rate'] for r in rows])\n"
             "plt.ylabel('pass rate'); plt.xticks(rotation=20); plt.title('baseline-v1'); plt.show()"),
        md("Category and difficulty breakdowns live in the same leaderboard JSON."),
    ])


def kaggle():
    return nb([
        md("# hdleval on Kaggle — Benchmark Evaluation, Statistics & Interpretation\n\n"
           "Demonstrates benchmark execution, experiment running, visualization, "
           "statistical analysis (Wilson intervals) and interpretation of results."),
        code(CLONE),
        code("!hdleval run configs/experiments/baseline.yaml --out results --db experiments/registry.sqlite | tail -2"),
        code("import json\n"
             "from hdleval.leaderboard.aggregate import wilson_interval\n"
             "lb = json.load(open('results/leaderboards/baseline-v1_leaderboard.json'))\n"
             "for r in lb['overall']:\n"
             "    print(f\"{r['model']:16s} pass={r['pass_rate']:.3f} CI={r['pass_ci95']}\")"),
        md("## Interpretation\n\nNon-overlapping confidence intervals separate the "
           "strongest and weakest configurations; pass rate declines with objective "
           "difficulty, concentrated on hard communication-protocol benchmarks."),
        code("import matplotlib.pyplot as plt\n"
             "rows = lb['overall']\n"
             "xs = [r['model'] for r in rows]\n"
             "ys = [r['pass_rate'] for r in rows]\n"
             "err = [[y-r['pass_ci95'][0] for y,r in zip(ys,rows)],\n"
             "       [r['pass_ci95'][1]-y for y,r in zip(ys,rows)]]\n"
             "plt.errorbar(xs, ys, yerr=err, fmt='o'); plt.xticks(rotation=20)\n"
             "plt.ylabel('pass rate'); plt.title('baseline-v1 with 95% CI'); plt.show()"),
    ])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "01_onboarding.ipynb": onboarding(),
        "02_benchmark_execution.ipynb": benchmark_execution(),
        "03_evaluation_harness.ipynb": evaluation_harness(),
        "04_reproduce.ipynb": reproduce(),
        "05_visualization.ipynb": visualization(),
        "kaggle_benchmark_evaluation.ipynb": kaggle(),
    }
    for name, obj in files.items():
        (OUT / name).write_text(json.dumps(obj, indent=1))
    print(f"wrote {len(files)} notebooks to {OUT}")


if __name__ == "__main__":
    main()

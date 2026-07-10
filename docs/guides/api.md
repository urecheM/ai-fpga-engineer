# API reference (overview)

| Module | Purpose | Key symbols |
|---|---|---|
| `hdleval.config` | typed config + YAML loading | `ExperimentConfig`, `load_experiment` |
| `hdleval.models` | inference providers | `ModelProvider`, `build_provider` |
| `hdleval.prompts` | prompt strategies | `build_prompt`, `build_repair_prompt` |
| `hdleval.parsing` | HDL extraction | `extract_vhdl` |
| `hdleval.benchmarks` | suite + difficulty | `load_suite`, `select`, `difficulty_score` |
| `hdleval.toolchain` | GHDL/Yosys adapters | `compile_vhdl`, `simulate`, `synthesize` |
| `hdleval.metrics` | static + resource metrics | `analyze_vhdl`, `resource_metrics` |
| `hdleval.verification` | properties + failures | `check_properties`, `classify_failure` |
| `hdleval.evaluation` | harness + runner | `EvaluationHarness`, `run_experiment` |
| `hdleval.registry` | provenance + DB | `ExperimentRecord`, `ExperimentDB` |
| `hdleval.leaderboard` | aggregation + stats | `build_leaderboard`, `wilson_interval` |
| `hdleval.reporting` | reports + figures | `write_all_reports`, `write_all_figures` |
| `hdleval.orchestration` | DAG execution | `DAG`, `Node` |
| `hdleval.plugins` | extensibility | `PluginRegistry`, `registry` |
| `hdleval.optimization` | objectives + Pareto | `pareto_frontier`, `score_design` |
| `hdleval.rag` | retrieval | `KnowledgeRetriever` |
| `hdleval.repair` | diagnosis | `diagnose` |

Generate HTML API docs with `pdoc hdleval` or `sphinx` in CI (planned).

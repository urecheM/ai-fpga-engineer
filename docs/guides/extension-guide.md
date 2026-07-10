# Extension guide

Everything extensible is registered through a plugin registry or a small factory.

## Add a model provider
1. Implement `ModelProvider` (`generate(ModelRequest) -> ModelResponse`).
2. Register a factory: `register_provider("myprov", factory)`.
3. Add `configs/models/mymodel.yaml` with `provider: myprov`.

## Add a benchmark
Create `benchmarks/v1/<id>/benchmark.yaml` (+ `reference.vhd`) or submit via the
benchmark-submission issue template. Fields: id, version, category, title,
specification, functional_requirements, entity, complexity, tags, properties.

## Add a prompt strategy
Extend `prompts/templates.py` (or add a plugin) and a `configs/prompts/*.yaml`.

## Add a synthesis/verification backend
Implement an adapter returning `ToolResult` / `PropertyReport` and register it
via `PluginKind.SYNTHESIS_BACKEND` / `PluginKind.VERIFICATION_ENGINE`.

## Add a metric
Add a pure function producing a serialisable dataclass and wire it into the
harness `metrics` dict. Keep it deterministic.

```bash
python reproduce.py
python reproduce.py --experiment configs/experiments/prompt-ablation.yaml
```
Steps: rebuild benchmarks, run experiment, generate publication...

## Determinism mechanisms
- Seeded providers. `reference` and `synthetic` are fully deterministic.
- Cached real-model responses. The `anthropic` provider hashes each request
  and caches the completion to `.hdleval_cache/`. re-runs read the cache.
- Environment fingerprint. OS, Python, machine, git commit recorded per run.

## Full-toolchain runs
Install the [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build) —
GHDL, Yosys and the ghdl-yosys-plugin in one tarball — or use the Docker
image, and set `HDLEVAL_REQUIRE_TOOLS=1` to make compile/synth/sim mandatory.
Otherwise those stages are `skipped` and recorded as such. Note that GHDL and
Yosys alone are not enough: without the plugin `detect().ghdl_plugin` is False
and synthesis is skipped even though both binaries are on PATH.

Verify the toolchain is complete before trusting any resource numbers:

```bash
python scripts/check_toolchain.py --synthesize
```

```bash
docker build -t hdleval . && docker run --rm -v "$PWD/results:/opt/hdleval/results" hdleval
```

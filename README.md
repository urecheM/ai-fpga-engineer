# hdleval: a reproducible benchmark for LLM-generated VHDL

An 18-circuit VHDL-2008 benchmark and a toolchain-backed evaluation harness. Each candidate is compiled, interface-checked, synthesised, placed and routed, simulated against golden vectors and, optionally, checked for formal equivalence with a verified reference. Every stage is scored separately.

# Corrected v1.0 release
- **Independent trials:** a per-trial run_seed replaces trials that were identical copies (effective n was 18, not 54)
- **Simulation on all 18 benchmarks:** golden-vector testbenches added for the 16 that had none. A skipped simulation is unverified instead of passing
- **Semantic faults:** fault types that compile replace syntax-only faults, so the static-only gap is now measured
- **Measured Fmax:** nextpnr results replace constant 100 MHz estimate. LUT/FF counts are populated
- **Statistics:** exact McNemar tests and a paired bootstrap are now implemented
- **Formal equivalence:** a SymbiYosys miter now runs on benchmark candidates
- **Toolchain enforcement:** HDLEVAL_REQUIRE_TOOLS=1 now raises an error when a tool is missing
- **Interface checks:** entity and port checks added. Regex "properties" are now lint and never graded

# Pipeline
spec -> prompt (+entity declaration) -> infer -> parse -> compile (GHDL) -> interface -> synthesise (Yosys) -> place and route (nextpnr, iCE40 UP5K) -> simulate (golden vectors) -> equivalence -> metrics -> lint -> classify -> record(sqlite)
- Run passes if its testbench passes or if no testbench ran and equivalence is proven
- Each failure gets one class, tool errors are subclassified

# Benchmark Suite
- Each benchmark has a spec, an expected interface, a verified reference and a self-checking testbench. Difficulty is a fixed weighted score that is never fitted to models (tiers: 1 trivial, 8 easy, 6 moderate, 3 hard). Reference Fmax ranges from 41.7 to 145.4 MHz.
- Parametric variants (adder width, FIFO width × depth, detector pattern) are generated per release from benchmarks/templates/ with a release seed, to limit memorisation. current release ships 9 variants (seed 2026)

# Quickstart
pip install -e ".[dev]"
hdleval run configs/experiments/baseline.yaml
hdleval run configs/experiments/baseline-semantic.yaml
python scripts/static_vs_toolchain_gap.py --experiment baseline-semantic-v1
python scripts/paired_stats.py --experiment baseline-v1

# Reproducibility
docker build -t hdleval . && docker run --rm hdleval
python reproduce.py

mit licensed
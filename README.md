# ai-fpga-engineer
# AI FPGA Engineer

> An autonomous multi-agent pipeline that turns a **plain-English request** into
> **verified, synthesizable VHDL** — with a block diagram, a self-checking
> testbench, an autonomous debug pass, resource/timing estimates, and a full
> engineering report, all with no human in the loop.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/self--tests-3%2F3%20passing-success)
![HDL](https://img.shields.io/badge/output-VHDL--2008-orange)

```bash
python -m ai_fpga_engineer.cli build "Design an 8-bit ALU supporting ADD, SUB, AND, OR, XOR"
```

```
=== AI FPGA Engineer  (LLM backend: offline-rule-based) ===
  · [requirements]  parsed request -> class='alu', width=8
  ✓ [requirements]  specification 'alu8': 3 inputs, 3 outputs, 5 ops
  ✓ [architecture]  rendered block diagram -> diagrams/alu8_block.svg
  ✓ [critic]        design review passed
  ✓ [hdl]           generated rtl/alu8.vhd  (opcode map: ADD=000 ... XOR=100)
  ✓ [verification]  309 test vectors; reference-model property checks passed
  ✓ [simulation]    emitted runnable GHDL flow under tb/
  ✓ [debug]         no defects detected; design is clean
  ✓ [optimization]  ~26 LUTs, Fmax≈490 MHz; best variant: baseline
  ✓ [documentation] reports/alu8_report.md
=== Pipeline OK ===
```

The project runs eight cooperating agents: requirements, architecture, design-review critic,
HDL generation, verification, simulation, autonomous debugging, optimization, and
documentation — over a shared project workspace, producing a complete, auditable
hardware design package for four design classes (**ALU, counter, comparator,
register**).

## Architecture


```
spec → architecture → critic → HDL → verification → simulation → debug → optimization → docs
```

Each agent has one responsibility and a narrow, typed interface, coordinated by an
orchestrator that owns sequencing, the design-review revision loop, optional fault
injection, and the final pass/fail decision. Every artifact is written through one
`Project` object, so the run is fully reproducible from its manifest.

## The correctness argument

For each design, `hdl/library.py` emits **both** the VHDL and a Python golden model
from the same description. Verification computes expected outputs with the model and
embeds them into the generated testbench. Therefore:

1. The golden model is property-checked in-container (and, in the test suite,
   re-validated against a *separately written* reference implementation).
2. A passing GHDL run proves the **RTL equals that model** on every vector.

A green simulation is then evidence the RTL matches a model independently shown to
satisfy the design's invariants — not a tautology.

## What's real vs. what's an extension point

**Real and checked here:** natural-language → formal spec, Graphviz block diagrams,
synthesizable VHDL-2008, golden-model + property-based verification over directed,
random, and exhaustive vectors, a self-checking testbench, an autonomous self-healing
debug loop, resource/timing estimation, and an offline TF-IDF knowledge base with
citations.

**Emitted for your toolchain:** this repo has no RTL simulator, so the pipeline
writes a ready-to-run **GHDL flow** (`tb/run_ghdl.sh`, `tb/Makefile`). If GHDL is
installed it runs automatically and reports the real result.

**Documented, not implemented (honest scope):** hardware-in-the-loop on real boards,
vendor synthesis/place-and-route, retrieval over copyrighted textbooks, a learned LLM
policy, and a React front end — each factored behind an existing interface.

## Quickstart

```bash
pip install -r ai_fpga_engineer/requirements.txt   # scikit-learn, numpy, Flask (core needs none)
# optional system tools: graphviz (dot), ghdl, gtkwave

python -m ai_fpga_engineer.cli build "Design a 16-bit ALU with ADD, SUB, AND, OR, XOR, NOT, INC, DEC" \
    --exhaustive --objective timing
python -m ai_fpga_engineer.cli ask "how do I raise Fmax?"
python -m ai_fpga_engineer.selftest                      # independent correctness checks
python -m ai_fpga_engineer.web.webapp --workdir ai_fpga_engineer/projects   # optional dashboard
```

To run the generated simulation (with GHDL installed):

```bash
cd <project>/tb && ./run_ghdl.sh      # or: make sim ; make wave
```

## Validation

- The canonical 8-bit/5-op ALU emits **309** vectors (**327,680** under
  `--exhaustive`); the 16-bit/8-op ALU emits **456**. Every embedded expected value
  matches a **separately written** reference implementation.
- All generated RTL is lint-clean; the self-healing loop detects and repairs an
  injected fault in one iteration.
- Bundled self-tests pass **3/3** and double as a regression guard.

## Read more


## Repository layout

```
ai_fpga_engineer/        the Python package (core, agents, hdl, sim, knowledge, web)
  TECHNICAL_REPORT.pdf   the deep-dive engineering report
  projects/alu8/         a real generated design (RTL, testbench, diagram, report)
README.md                this file
LICENSE                  MIT
```

## License

MIT — see [LICENSE](LICENSE).

---

*Built as a portfolio project to demonstrate agentic system design, HDL generation,
and a verification-first approach to trusting machine-generated hardware.*

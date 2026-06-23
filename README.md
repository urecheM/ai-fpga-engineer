# ai-fpga-engineer
# AI FPGA Engineer

> An autonomous multi-agent pipeline that converts natural-language hardware
> requirements into verified, synthesizable VHDL.

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


## The correctness argument

For each design, `hdl/library.py` emits **both** the VHDL and a Python golden model
from the same description. Verification computes expected outputs with the model and
embeds them into the generated testbench. Therefore:

1. The golden model is property-checked in-container (and, in the test suite,
   re-validated against a *separately written* reference implementation).
2. A passing GHDL run proves the **RTL equals that model** on every vector.

A green simulation is then evidence the RTL matches a model independently shown to
satisfy the design's invariants — not a tautology.

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

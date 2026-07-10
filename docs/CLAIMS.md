# Claim → Evidence Map

Rule: **if CI does not prove it, the README does not say it.** Every capability
claim below names the artifact or CI job that backs it. Vocabulary is chosen to
match the evidence, not to flatter it.

| Claim | Evidence | Where |
|-------|----------|-------|
| The emitted VHDL is functionally correct against the spec | GHDL compiles and executes the RTL against oracle-derived expected values; CI requires this (`AIFPGA_REQUIRE_TOOLS=1`) | selftest checks 1, 7, 8; CI job `test` |
| The verification harness can actually detect wrongness | Negative test: a seeded stuck-carry bug (invisible to model-level checks) makes GHDL simulation FAIL | selftest check 8 |
| Detection coverage across defect classes | Mutation campaign: 8 independent defect classes seeded; first detecting stage reported per class, **escapes reported honestly** | `cli mutation-campaign`; CI artifact `reports/mutation_report.md` |
| Timing/area numbers are real | QoR `source == "nextpnr-ice40"`: SB_LUT4/SB_DFF counts and achieved Fmax from place-and-route on iCE40 UP5K (seed 1, deterministic) | `sim/pnr.py`; report section 13 |
| The closed loop meets timing targets | Target derived from *measured* Fmax of two real variants (midpoint); loop accepted on measured numbers | selftest check 7 |
| The estimator is useful (and its error is known) | Calibration sweep: estimated vs measured across the design space; MAPE and Fmax scale ratio published | `cli calibrate`; CI artifact `reports/calibration/` |
| Class invariants hold on the RTL (bounded) | SymbiYosys BMC (depth 24) on a synthesizable formal wrapper of the actual DUT; parsed PASS recorded | `formal/*.sby`, selftest check 9 |
| Class invariants hold on the reference model | Exhaustive (<=10-bit) or bounded Python model checks — labelled `model_*`, which make **no claim about the VHDL** | formal report table |
| The self-healing loop repairs defects | Repairs demonstrated on *lint-fixable* classes only; non-fixable classes are flagged, not silently fixed | selftest check 10; mutation report; `agents/debug_agent.py` |

## Vocabulary

- **model_exhaustive / model_bounded** — a software check of the reference
  oracle. Says nothing about the VHDL.
- **RTL BMC pass (depth N)** — SymbiYosys found no counterexample within N
  cycles on the emitted RTL. A bounded result; "proven" (unbounded, via
  k-induction) is future work and is never claimed.
- **measured / estimated** — every QoR record carries its `source`. Only
  `nextpnr-ice40` numbers are measurements.

## Oracle independence (dedup rationale)

There is exactly ONE golden model per design class (`reference/models.py`);
the old duplicated per-module oracles are gone. Independence is established not
by re-implementing the oracle but by (a) GHDL executing the *emitted RTL* — an
independent artifact — against oracle values, and (b) the mutation campaign
demonstrating that RTL-side deviations are caught.

## Confidence formulas (report section 14)

- `requirements`: 0.9 if the request mapped to a known design class, 0.3 otherwise.
- `verification`: 1.0 = GHDL ran and passed; 0.6 = model-level only; 0.0 = any failure.
- `hdl`: 1.0 = critic clean; 0.4 otherwise. `debug`: 1.0 = final clean; 0.0 otherwise.
- `qor`: 1.0 = measured source; 0.5 = estimated.
- `formal`: 0 on any failure; up to 0.7 from model checks; 0.9 with a passing
  RTL-level BMC; 1.0 reserved for unbounded proof (not yet claimed).
- Overall = minimum over stages (weakest-link).

## Known limitations (stated, not hidden)

- Four template-based design classes; the pipeline is **rule-based** (no learning).
- Exhaustive checking collapses past ~10-bit operands; wider designs get bounded
  checks, labelled as such. Embedded testbenches cap at 2048 vectors.
- Rule-based repair covers only mechanically fixable defects; semantic defects
  are diagnosed and flagged.
- Formal coverage is invariants + transition relations, BMC-bounded; single
  device family (iCE40 UP5K), no on-silicon validation yet.

| Claim | Evidence | Where |
|-------|----------|-------|
| The emitted VHDL is functionally correct against the spec | GHDL compiles and executes the RTL against oracle-derived expected values; hard-required via `AIFPGA_REQUIRE_TOOLS=1` | selftest checks 1, 7, 8 |
| The verification harness detects wrongness | Negative test: a seeded stuck-carry bug (invisible to model-level checks) makes GHDL simulation FAIL | selftest check 8 |
| Detection coverage across defect classes | Mutation campaign: 8 independent defect classes seeded; first detecting stage reported per class, escapes reported | `cli mutation-campaign`; artifact `reports/mutation_report.md` |
| Real timing/area numbers | QoR `source == "nextpnr-ice40"`: SB_LUT4/SB_DFF counts and achieved Fmax from place-and-route on iCE40 UP5K (seed 1, deterministic) | `sim/pnr.py`; report section 13 |
| The closed loop meets timing targets | Target derived from measured Fmax of two real variants (midpoint); loop accepted on measured numbers | selftest check 7 |
| The estimator is useful and its error is known | Calibration sweep: estimated vs measured across the design space; MAPE and Fmax scale ratio published | `cli calibrate`; artifact `reports/calibration/` |
| Class invariants hold on the RTL (bounded) | SymbiYosys BMC (depth 24) on a synthesizable formal wrapper of the actual DUT; parsed PASS recorded | `formal/*.sby`, selftest check 9 |
| Class invariants hold on the reference model | Exhaustive (<=10-bit) or bounded Python model checks — labelled `model_*` | formal report table |
| The self-healing loop repairs defects | Repairs demonstrated on lint-fixable classes only; non-fixable classes are flagged | selftest check 10; mutation report; `ai_fpga_engineer/agents/debug_agent.py` |

## Oracle independence (dedup rationale)
There is exactly one golden model per design class (`ai_fpga_engineer/reference/models.py`). Independence is established by (a) GHDL executing the emitted RTL (an
independent artifact) against oracle values and (b) the mutation campaign
demonstrating that RTL-side deviations are caught.

## Confidence formulae

- `requirements`: 0.9 if the request mapped to a known design class, 0.3 otherwise.
- `verification`: 1.0 = GHDL ran and passed; 0.6 = model-level only; 0.0 = any failure.
- `hdl`: 1.0 = critic clean; 0.4 otherwise. `debug`: 1.0 = final clean; 0.0 otherwise.
- `qor`: 1.0 = measured source; 0.5 = estimated.
- `formal`: 0 on any failure; up to 0.7 from model checks; 0.9 with a passing
  RTL-level BMC; 1.0 reserved for unbounded proof (not yet claimed).
- Overall = minimum over stages (weakest-link).

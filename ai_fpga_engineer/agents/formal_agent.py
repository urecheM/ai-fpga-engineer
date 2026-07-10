"""Formal verification stage — with an honest vocabulary.

The previous version called exhaustive Python-model checking "proven" and
emitted a SymbiYosys flow that was never executed (and could not run as
written). Both problems are fixed here:

1. **Model checks** (in-container, no tools needed) exhaustively or boundedly
   check the *reference model's* class invariants. Their statuses are now
   ``model_exhaustive`` / ``model_bounded`` / ``failed`` — they are strong
   software checks of the oracle, and are labelled as exactly that. The word
   "proven" is reserved for a model checker discharging properties on RTL.

2. **A real SymbiYosys task on the actual VHDL.** A synthesizable formal
   wrapper (``formal/<e>_formal.vhd``) instantiates the DUT and states the
   class invariants as native VHDL-2008 PSL assertions over pre-computed
   boolean signals (the most portable subset for GHDL synthesis — no ``prev()``,
   no vunit files). The ``.sby`` task loads the GHDL plugin explicitly and is
   executed by this agent whenever ``sby`` is installed; the parsed PASS/FAIL
   is recorded as ``sby_status``. Mode is BMC (depth 24): a bounded proof on
   the RTL, reported as such; extending to k-induction is listed as future
   work rather than implied.
"""
from __future__ import annotations

import random
import subprocess
from dataclasses import dataclass, field

from .base import Agent
from ..core.project import Project
from ..core.spec import Specification
from ..core import toolchain
from ..hdl.library import GeneratedDesign
from ..reference import models as ref

EXHAUSTIVE_WIDTH_LIMIT = 10   # 2^(2W) operand space stays tractable up to here
SBY_DEPTH = 24


@dataclass
class Property:
    name: str
    status: str        # "model_exhaustive" | "model_bounded" | "failed"
    method: str

    def to_dict(self) -> dict:
        return {"name": self.name, "status": self.status, "method": self.method}


@dataclass
class FormalResult:
    properties: list[Property] = field(default_factory=list)
    wrapper_path: str = ""
    sby_path: str = ""
    psl_path: str = ""                    # kept for compatibility (= wrapper_path)
    sby_status: str = "not_run"           # "pass" | "fail" | "error" | "not_run"
    sby_log: str = ""

    @property
    def any_failed(self) -> bool:
        return any(p.status == "failed" for p in self.properties) or self.sby_status == "fail"

    @property
    def all_model_exhaustive(self) -> bool:
        return bool(self.properties) and all(p.status == "model_exhaustive"
                                             for p in self.properties)

    @property
    def confidence(self) -> float:
        """Evidence-based: 0 on any failure; model checks give up to 0.7
        (exhaustive) / 0.45 (bounded); a passing RTL-level BMC lifts to 0.9.
        1.0 is reserved for unbounded proof (k-induction) — future work."""
        if not self.properties:
            return 0.0
        if self.any_failed:
            return 0.0
        exhaustive = sum(1 for p in self.properties if p.status == "model_exhaustive")
        base = 0.7 * (exhaustive / len(self.properties)) \
            + 0.45 * (1 - exhaustive / len(self.properties))
        return round(max(base, 0.9) if self.sby_status == "pass" else base, 3)

    def label(self) -> str:
        if self.any_failed:
            return "FAILED"
        bits = []
        if self.properties:
            ex = sum(1 for p in self.properties if p.status == "model_exhaustive")
            bits.append(f"model: {ex}/{len(self.properties)} exhaustive")
        bits.append({"pass": f"RTL BMC pass (depth {SBY_DEPTH})",
                     "fail": "RTL BMC FAIL",
                     "error": "RTL BMC error",
                     "not_run": "RTL BMC not run (sby absent)"}[self.sby_status])
        return "; ".join(bits)


class FormalAgent(Agent):
    name = "formal"

    def run(self, project: Project, spec: Specification,
            design: GeneratedDesign) -> FormalResult:
        checkers = {"alu": self._model_alu, "comparator": self._model_comparator,
                    "counter": self._model_counter, "register": self._model_register}
        props = checkers.get(spec.design_class, lambda *_: [])(spec, design)

        wrapper = self._wrapper(spec, design)
        result = FormalResult(props)
        if wrapper:
            wrapper_rel = f"formal/{design.entity}_formal.vhd"
            project.write(wrapper_rel, wrapper, "formal_wrapper")
            project.write(f"formal/{design.entity}.sby", self._sby(design), "formal_sby")
            project.write("formal/README.md", self._readme(design), "formal_readme")
            result.wrapper_path = wrapper_rel
            result.psl_path = wrapper_rel
            result.sby_path = f"formal/{design.entity}.sby"
            result.sby_status, result.sby_log = self._run_sby(project, design)

        if result.any_failed:
            self.log(project, f"FORMAL FAILURE: {result.label()}", "error")
        else:
            self.log(project, result.label(), "success")
        self._write(project, design, result)
        return result

    # ------------------------------------------------------------------
    # SymbiYosys execution
    # ------------------------------------------------------------------
    def _run_sby(self, project: Project, design: GeneratedDesign) -> tuple[str, str]:
        tc = toolchain.detect()
        if not tc.formal_ok:
            why = "sby not installed" if not tc.present.get("sby") else "GHDL plugin unavailable"
            if toolchain.require_tools():
                raise RuntimeError(f"AIFPGA_REQUIRE_TOOLS=1 but formal tools missing: {why}")
            self.log(project, f"SymbiYosys not run ({why}); task emitted for local runs", "warn")
            return "not_run", ""
        try:
            out = subprocess.run(["sby", "-f", f"{design.entity}.sby"],
                                 cwd=str(project.root / "formal"),
                                 capture_output=True, text=True, timeout=900)
        except Exception as exc:
            return "error", f"sby invocation failed: {exc}"
        log = out.stdout + out.stderr
        if "DONE (PASS" in log:
            return "pass", log
        if "DONE (FAIL" in log:
            return "fail", log
        return "error", log

    # ------------------------------------------------------------------
    # Model checks (oracle invariants; honest statuses)
    # ------------------------------------------------------------------
    def _alu_fn(self, design: GeneratedDesign):
        if design.kind == "combinational":
            return lambda a, b, op: design.eval_fn({"a": a, "b": b, "op": op})
        return lambda a, b, op: design.run_fn([{"a": a, "b": b, "op": op}])[0]

    def _model_alu(self, spec, design) -> list[Property]:
        W = spec.data_width
        mask = (1 << W) - 1
        ops = [o.name for o in spec.operations] or ["ADD", "SUB", "AND", "OR", "XOR"]
        f = self._alu_fn(design)
        exhaustive = W <= EXHAUSTIVE_WIDTH_LIMIT
        method = (f"model check, exhaustive over all {1 << (2 * W)} operand pairs x "
                  f"{len(ops)} ops" if exhaustive
                  else "model check, 20000 random vectors (width too large for exhaustive)")
        if exhaustive:
            space = ((a, b, op) for op in ops for a in range(1 << W) for b in range(1 << W))
        else:
            rng = random.Random(2024)
            space = ((rng.randint(0, mask), rng.randint(0, mask), rng.choice(ops))
                     for _ in range(20000))
        zero_ok = carry_ok = range_ok = equiv_ok = True
        for a, b, op in space:
            e = f(a, b, op)
            r, c, z = e["result"], e["carry"], e["zero"]
            if z != ref.alu_zero(r):
                zero_ok = False
            if c not in (0, 1):
                carry_ok = False
            if not (0 <= r <= mask):
                range_ok = False
            if (r, c) != ref.alu(op, a, b, W):
                equiv_ok = False
        st = "model_exhaustive" if exhaustive else "model_bounded"
        return [Property("zero_flag_iff_result_zero", st if zero_ok else "failed", method),
                Property("carry_is_single_bit", st if carry_ok else "failed", method),
                Property("result_within_width", st if range_ok else "failed", method),
                Property("matches_reference_semantics", st if equiv_ok else "failed", method)]

    def _model_comparator(self, spec, design) -> list[Property]:
        W = spec.data_width
        mask = (1 << W) - 1
        f = (lambda a, b: design.eval_fn({"a": a, "b": b})) if design.kind == "combinational" \
            else (lambda a, b: design.run_fn([{"a": a, "b": b}])[0])
        exhaustive = W <= EXHAUSTIVE_WIDTH_LIMIT
        method = (f"model check, exhaustive over all {1 << (2 * W)} pairs" if exhaustive
                  else "model check, 20000 random pairs")
        rng = random.Random(7)
        space = ([(a, b) for a in range(1 << W) for b in range(1 << W)] if exhaustive
                 else [(rng.randint(0, mask), rng.randint(0, mask)) for _ in range(20000)])
        onehot_ok = correct_ok = True
        for a, b in space:
            e = f(a, b)
            if e["gt"] + e["eq"] + e["lt"] != 1:
                onehot_ok = False
            if (e["gt"], e["eq"], e["lt"]) != ref.comparator(a, b):
                correct_ok = False
        st = "model_exhaustive" if exhaustive else "model_bounded"
        return [Property("outputs_are_one_hot", st if onehot_ok else "failed", method),
                Property("relation_is_correct", st if correct_ok else "failed", method)]

    def _model_counter(self, spec, design) -> list[Property]:
        W = spec.data_width
        mask = (1 << W) - 1
        exhaustive = W <= 12
        seq = [{"rst": 1, "en": 0}] + [{"rst": 0, "en": 1} for _ in range(mask + 2)]
        seq += [{"rst": 0, "en": 0}, {"rst": 0, "en": 1}]
        outs = design.run_fn(seq)
        state, oks = 0, {"count_within_range": True, "zero_after_reset": True,
                         "terminal_count_correct": True, "transition_matches_reference": True}
        for s, e in zip(seq, outs):
            state, tc = ref.counter_step(state, s.get("rst", 0), s.get("en", 0), W)
            if not (0 <= e["count"] <= mask):
                oks["count_within_range"] = False
            if s.get("rst") and e["count"] != 0:
                oks["zero_after_reset"] = False
            if e["tc"] != (1 if e["count"] == mask else 0):
                oks["terminal_count_correct"] = False
            if (e["count"], e["tc"]) != (state, tc):
                oks["transition_matches_reference"] = False
        st = "model_exhaustive" if exhaustive else "model_bounded"
        m = (f"model check, reachability over all {mask + 1} states" if exhaustive
             else "model check, partial reachability")
        return [Property(k, st if v else "failed", m) for k, v in oks.items()]

    def _model_register(self, spec, design) -> list[Property]:
        W = spec.data_width
        mask = (1 << W) - 1
        rng = random.Random(99)
        data = sorted({0, 1, mask, mask >> 1} | {rng.randint(0, mask) for _ in range(32)})
        seq = [{"rst": 1, "en": 0, "d": 0}]
        for dv in data:
            seq += [{"rst": 0, "en": 1, "d": dv},
                    {"rst": 0, "en": 0, "d": rng.randint(0, mask)}]
        seq.append({"rst": 1, "en": 0, "d": rng.randint(0, mask)})
        outs = design.run_fn(seq)
        state, ok = 0, True
        for s, e in zip(seq, outs):
            state = ref.register_step(state, s.get("rst", 0), s.get("en", 0), s.get("d", 0), W)
            if e["q"] != state:
                ok = False
        m = "model check, reset/load/hold sequence with representative data"
        return [Property("transition_matches_reference", "model_bounded" if ok else "failed", m)]

    # ------------------------------------------------------------------
    # RTL-level formal wrapper (synthesizable VHDL-2008 + native PSL)
    # ------------------------------------------------------------------
    def _wrapper(self, spec: Specification, design: GeneratedDesign) -> str | None:
        builders = {"alu": self._wrap_alu, "comparator": self._wrap_comparator,
                    "counter": self._wrap_counter, "register": self._wrap_register}
        fn = builders.get(spec.design_class)
        return fn(spec, design) if fn else None

    @staticmethod
    def _hdr(e: str) -> str:
        return (f"""library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

-- Formal wrapper for {e} (generated by AI FPGA Engineer).
-- Class invariants are stated as native VHDL-2008 PSL assertions over
-- pre-computed boolean signals (portable subset for GHDL synthesis).
""")

    def _wrap_alu(self, spec, design) -> str:
        e = design.entity
        W = spec.data_width
        opw = next(p.width for p in design.ports if p.name == "op")
        clk_assoc = "clk => clk, " if any(p.role == "clock" for p in design.ports) else ""
        return self._hdr(e) + f"""entity {e}_formal is
    port (
        clk : in std_logic;
        a   : in std_logic_vector({W - 1} downto 0);
        b   : in std_logic_vector({W - 1} downto 0);
        op  : in std_logic_vector({opw - 1} downto 0)
    );
end entity {e}_formal;

architecture formal of {e}_formal is
    signal result : std_logic_vector({W - 1} downto 0);
    signal carry, zero : std_logic;
    signal valid : std_logic := '0';
    signal ok_zero : std_logic;
begin
    dut: entity work.{e}
        port map ({clk_assoc}a => a, b => b, op => op,
                  result => result, carry => carry, zero => zero);

    process(clk) begin
        if rising_edge(clk) then valid <= '1'; end if;
    end process;

    ok_zero <= '1' when ((zero = '1') = (unsigned(result) = 0)) else '0';

    default clock is rising_edge(clk);
    -- zero flag is asserted exactly when the result is zero
    assert always ((valid = '1') -> (ok_zero = '1'));
end architecture formal;
"""

    def _wrap_comparator(self, spec, design) -> str:
        e = design.entity
        W = spec.data_width
        registered = design.latency >= 1
        clk_assoc = "clk => clk, " if any(p.role == "clock" for p in design.ports) else ""
        ref_sig = ("    signal a_r, b_r : std_logic_vector"
                   f"({W - 1} downto 0) := (others => '0');\n" if registered else "")
        ref_upd = "            a_r <= a; b_r <= b;\n" if registered else ""
        a_ref, b_ref = ("a_r", "b_r") if registered else ("a", "b")
        return self._hdr(e) + f"""entity {e}_formal is
    port (
        clk : in std_logic;
        a   : in std_logic_vector({W - 1} downto 0);
        b   : in std_logic_vector({W - 1} downto 0)
    );
end entity {e}_formal;

architecture formal of {e}_formal is
    signal gt, eq, lt : std_logic;
    signal valid : std_logic := '0';
{ref_sig}    signal ok_onehot, ok_rel : std_logic;
begin
    dut: entity work.{e}
        port map ({clk_assoc}a => a, b => b, gt => gt, eq => eq, lt => lt);

    process(clk) begin
        if rising_edge(clk) then
            valid <= '1';
{ref_upd}        end if;
    end process;

    ok_onehot <= (gt xor eq xor lt) and not (gt and eq and lt);
    ok_rel <= '1' when ((gt = '1') = (unsigned({a_ref}) > unsigned({b_ref})))
                   and ((eq = '1') = (unsigned({a_ref}) = unsigned({b_ref})))
                   and ((lt = '1') = (unsigned({a_ref}) < unsigned({b_ref})))
              else '0';

    default clock is rising_edge(clk);
    assert always ((valid = '1') -> (ok_onehot = '1'));
    assert always ((valid = '1') -> (ok_rel = '1'));
end architecture formal;
"""

    def _wrap_counter(self, spec, design) -> str:
        e = design.entity
        W = spec.data_width
        return self._hdr(e) + f"""entity {e}_formal is
    port (
        clk : in std_logic;
        rst : in std_logic;
        en  : in std_logic
    );
end entity {e}_formal;

architecture formal of {e}_formal is
    signal count : std_logic_vector({W - 1} downto 0);
    signal tc    : std_logic;
    signal p_count : unsigned({W - 1} downto 0) := (others => '0');
    signal p_rst, p_en, valid : std_logic := '0';
    signal ok_trans, ok_tc : std_logic;
begin
    dut: entity work.{e}
        port map (clk => clk, rst => rst, en => en, count => count, tc => tc);

    -- sample the pre-edge state and the inputs that produce the next state
    process(clk) begin
        if rising_edge(clk) then
            p_count <= unsigned(count);
            p_rst   <= rst;
            p_en    <= en;
            valid   <= '1';
        end if;
    end process;

    -- transition relation: count = f(previous count, applied rst/en)
    ok_trans <= '1' when
        (p_rst = '1' and unsigned(count) = 0) or
        (p_rst = '0' and p_en = '1' and unsigned(count) = p_count + 1) or
        (p_rst = '0' and p_en = '0' and unsigned(count) = p_count)
        else '0';
    ok_tc <= '1' when ((tc = '1') = (count = (count'range => '1'))) else '0';

    default clock is rising_edge(clk);
    assert always ((valid = '1') -> (ok_trans = '1'));
    assert always (ok_tc = '1');
end architecture formal;
"""

    def _wrap_register(self, spec, design) -> str:
        e = design.entity
        W = spec.data_width
        return self._hdr(e) + f"""entity {e}_formal is
    port (
        clk : in std_logic;
        rst : in std_logic;
        en  : in std_logic;
        d   : in std_logic_vector({W - 1} downto 0)
    );
end entity {e}_formal;

architecture formal of {e}_formal is
    signal q : std_logic_vector({W - 1} downto 0);
    signal p_q, p_d : std_logic_vector({W - 1} downto 0) := (others => '0');
    signal p_rst, p_en, valid : std_logic := '0';
    signal ok_trans : std_logic;
begin
    dut: entity work.{e}
        port map (clk => clk, rst => rst, en => en, d => d, q => q);

    process(clk) begin
        if rising_edge(clk) then
            p_q <= q; p_d <= d; p_rst <= rst; p_en <= en; valid <= '1';
        end if;
    end process;

    ok_trans <= '1' when
        (p_rst = '1' and unsigned(q) = 0) or
        (p_rst = '0' and p_en = '1' and q = p_d) or
        (p_rst = '0' and p_en = '0' and q = p_q)
        else '0';

    default clock is rising_edge(clk);
    assert always ((valid = '1') -> (ok_trans = '1'));
end architecture formal;
"""

    # ------------------------------------------------------------------
    def _sby(self, design: GeneratedDesign) -> str:
        e = design.entity
        return f"""# SymbiYosys task for {e} (generated by AI FPGA Engineer).
# Bounded model check of the RTL-level class invariants, depth {SBY_DEPTH}.
# Requires the OSS CAD Suite (sby, yosys with GHDL plugin, ghdl).
# Run from this directory:  sby -f {e}.sby
[options]
mode bmc
depth {SBY_DEPTH}

[engines]
smtbmc

[script]
plugin -i ghdl
ghdl --std=08 {e}.vhd {e}_formal.vhd -e {e}_formal
prep -top {e}_formal

[files]
../rtl/{e}.vhd
{e}_formal.vhd
"""

    def _readme(self, design: GeneratedDesign) -> str:
        e = design.entity
        return f"""# Formal verification flow — {e}

- `{e}_formal.vhd` — synthesizable wrapper stating the class invariants as
  native VHDL-2008 PSL assertions on the *actual DUT RTL*.
- `{e}.sby` — SymbiYosys bounded model check (depth {SBY_DEPTH}).

When `sby` is installed the pipeline runs this itself and records the parsed
PASS/FAIL in the report (`sby_status`). Manual run: `sby -f {e}.sby`.

Vocabulary note: the report distinguishes **model checks** (exhaustive/bounded
checks of the reference model, in Python) from this **RTL-level BMC**. Only the
latter says anything about the VHDL. Extending BMC to unbounded proof via
k-induction is future work.
"""

    def _write(self, project: Project, design: GeneratedDesign, result: FormalResult) -> None:
        lines = [f"# Formal Verification — {design.entity}", "",
                 f"**Summary: {result.label()}.**", "",
                 "Model checks validate the reference model's invariants in software; the "
                 "SymbiYosys task checks the same invariants on the *emitted RTL* (bounded, "
                 f"depth {SBY_DEPTH}). Statuses are labelled accordingly — `model_*` results "
                 "make no claim about the VHDL.", "",
                 "| property | status | method |", "|----------|--------|--------|"]
        for p in result.properties:
            lines.append(f"| `{p.name}` | {p.status} | {p.method} |")
        lines += ["", f"RTL-level BMC (`sby`): **{result.sby_status}**"
                  + (f" — see `{result.sby_path}`." if result.sby_path else ".")]
        project.write(f"docs/{design.entity}_formal.md", "\n".join(lines), "formal_report")
        if result.sby_log:
            project.write(f"formal/{design.entity}_sby.log", result.sby_log, "formal_sby_log")

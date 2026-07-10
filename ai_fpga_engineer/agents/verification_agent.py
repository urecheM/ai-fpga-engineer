"""Verification agent.

Two layers, kept deliberately distinct (vocabulary matters — see docs/CLAIMS.md):

1. **Model-level property checks** — the design's golden model is exercised on
   the test plan and checked against the reference oracle
   (:mod:`ai_fpga_engineer.reference.models`). These validate the *model* and
   the vector set; they say nothing about the VHDL.

2. **A self-checking VHDL testbench** with the oracle's expected values
   embedded as constants. When GHDL executes it (sim/runner.py), the *emitted
   RTL* — an independent artifact — is checked vector-by-vector against the
   oracle. The testbench drives its own clock from the stimulus process, so
   simulation terminates naturally, prints ``ALL TESTS PASSED`` or fails with
   severity ``failure`` (non-zero exit), and needs no stop-time flags.

The mutation campaign relies on this split: a seeded RTL bug is invisible to
layer 1 by construction and must be caught by layer 2.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .base import Agent
from ..core.spec import Specification
from ..hdl import library
from ..hdl.library import GeneratedDesign
from ..reference import models as ref

TB_MAX_VECTORS = 2048   # embedded-constant testbench size cap (exhaustive plans
                        # keep full coverage at the model layer; the TB samples)


@dataclass
class VerificationResult:
    total: int
    passed: bool
    property_failures: list[str] = field(default_factory=list)
    tb_entity: str = ""
    tb_vectors: int = 0


class VerificationAgent(Agent):
    name = "verification"

    def run(self, project, spec: Specification, design: GeneratedDesign,
            exhaustive: bool = False) -> VerificationResult:
        plan = design.default_plan
        if exhaustive and spec.design_class == "alu" and design.kind == "combinational":
            plan = library.alu_exhaustive_plan(spec)
        vectors = plan.vectors
        expected = ([design.eval_fn(v) for v in vectors] if design.eval_fn
                    else design.run_fn(vectors))

        failures = self._property_checks(spec, vectors, expected)

        tb_vecs, tb_exp = vectors[:TB_MAX_VECTORS], expected[:TB_MAX_VECTORS]
        e = design.entity
        project.write(f"tb/{e}_vectors.json",
                      json.dumps({"vectors": tb_vecs, "expected": tb_exp}),
                      "test_vectors")
        project.write(f"tb/{e}_tb.vhd", self._testbench(design, tb_vecs, tb_exp),
                      "testbench")

        status = "PASS" if not failures else f"FAIL ({len(failures)} violation(s))"
        self.log(project, f"{len(vectors)} vectors; oracle property checks: {status}; "
                          f"self-checking testbench tb/{e}_tb.vhd "
                          f"({len(tb_vecs)} embedded vectors)",
                 "success" if not failures else "error")
        return VerificationResult(len(vectors), not failures, failures,
                                  f"{e}_tb", len(tb_vecs))

    # ------------------------------------------------------------------
    # Layer 1: model vs oracle
    # ------------------------------------------------------------------
    def _property_checks(self, spec, vectors, expected) -> list[str]:
        fails: list[str] = []

        def add(msg):
            if len(fails) < 5:
                fails.append(msg)

        W = spec.data_width
        if spec.design_class == "alu":
            for v, e in zip(vectors, expected):
                r, c = ref.alu(v["op"], v["a"], v["b"], W)
                if (e["result"], e["carry"]) != (r, c):
                    add(f"{v['op']}(a={v['a']}, b={v['b']}): model gave "
                        f"({e['result']},{e['carry']}), oracle ({r},{c})")
                if e["zero"] != ref.alu_zero(e["result"]):
                    add(f"zero flag wrong for result {e['result']}")
        elif spec.design_class == "comparator":
            for v, e in zip(vectors, expected):
                if (e["gt"], e["eq"], e["lt"]) != ref.comparator(v["a"], v["b"]):
                    add(f"compare(a={v['a']}, b={v['b']}) wrong")
                if e["gt"] + e["eq"] + e["lt"] != 1:
                    add(f"outputs not one-hot at a={v['a']}, b={v['b']}")
        elif spec.design_class == "counter":
            state = 0
            for v, e in zip(vectors, expected):
                state, tc = ref.counter_step(state, v.get("rst", 0), v.get("en", 0), W)
                if (e["count"], e["tc"]) != (state, tc):
                    add(f"counter transition wrong at input {v}")
        elif spec.design_class == "register":
            state = 0
            for v, e in zip(vectors, expected):
                state = ref.register_step(state, v.get("rst", 0), v.get("en", 0),
                                          v.get("d", 0), W)
                if e["q"] != state:
                    add(f"register transition wrong at input {v}")
        return fails

    # ------------------------------------------------------------------
    # Layer 2: self-checking VHDL testbench
    # ------------------------------------------------------------------
    def _testbench(self, design: GeneratedDesign, vectors, expected) -> str:
        e = design.entity
        ins = [p for p in design.ports if p.direction == "in" and p.role != "clock"]
        outs = [p for p in design.ports if p.direction == "out"]
        has_clk = any(p.role == "clock" for p in design.ports)
        opmap = design.opcode_map

        def bits(value: int, width: int) -> str:
            return format(value & ((1 << width) - 1), f"0{width}b")

        def field_val(p, v):
            raw = v.get(p.name, 0)
            if p.name == "op" and opmap:
                return opmap[raw] if isinstance(raw, str) else bits(raw, p.width)
            return bits(int(raw), p.width)

        def lit(p, s: str) -> str:
            return f"'{s}'" if p.width == 1 else f'"{s}"'

        rec_fields = "\n".join(
            [f"        {p.name} : "
             + ("std_logic" if p.width == 1
                else f"std_logic_vector({p.width - 1} downto 0)") + ";"
             for p in ins]
            + [f"        e_{p.name} : "
               + ("std_logic" if p.width == 1
                  else f"std_logic_vector({p.width - 1} downto 0)") + ";"
               for p in outs])

        rows = []
        for v, x in zip(vectors, expected):
            parts = [f"{p.name} => {lit(p, field_val(p, v))}" for p in ins]
            parts += [f"e_{p.name} => {lit(p, bits(int(x[p.name]), p.width))}"
                      for p in outs]
            rows.append("        (" + ", ".join(parts) + ")")
        if len(rows) == 1:
            rows[0] = "        0 => " + rows[0].strip()
        vec_table = ",\n".join(rows)

        sigs = []
        if has_clk:
            sigs.append("    signal clk : std_logic := '0';")
        for p in ins + outs:
            t = ("std_logic" if p.width == 1
                 else f"std_logic_vector({p.width - 1} downto 0)")
            sigs.append(f"    signal s_{p.name} : {t};")

        assoc = []
        if has_clk:
            assoc.append("clk => clk")
        assoc += [f"{p.name} => s_{p.name}" for p in ins + outs]

        drive = "\n".join(f"            s_{p.name} <= VECS(i).{p.name};" for p in ins)
        if has_clk:
            advance = ("            clk <= '0';\n"
                       "            wait for 5 ns;\n"
                       "            clk <= '1';\n"
                       "            wait for 5 ns;")
        else:
            advance = "            wait for 2 ns;"
        checks = "\n".join(
            f"""            if s_{p.name} /= VECS(i).e_{p.name} then
                errors := errors + 1;
                report "vector " & integer'image(i) & ": {p.name} mismatch"
                    severity error;
            end if;""" for p in outs)

        return f"""library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

-- Self-checking testbench for {e} (generated by AI FPGA Engineer).
-- Expected values are embedded from the spec-derived reference oracle
-- (ai_fpga_engineer/reference/models.py); a GHDL pass therefore establishes
-- RTL/oracle agreement on every embedded vector. The stimulus process drives
-- its own clock, so simulation terminates naturally. A mismatch ends the run
-- with severity failure (non-zero exit code).
entity {e}_tb is
end entity {e}_tb;

architecture tb of {e}_tb is
    type vec_t is record
{rec_fields}
    end record;
    type vec_arr_t is array (natural range <>) of vec_t;
    constant VECS : vec_arr_t := (
{vec_table}
    );

{chr(10).join(sigs)}
begin
    dut: entity work.{e}
        port map ({", ".join(assoc)});

    stim: process
        variable errors : natural := 0;
    begin
        for i in VECS'range loop
{drive}
{advance}
{checks}
        end loop;
        if errors = 0 then
            report "ALL TESTS PASSED (" & integer'image(VECS'length)
                & " vectors)" severity note;
        else
            report integer'image(errors) & " vector(s) FAILED"
                severity failure;
        end if;
        wait;
    end process;
end architecture tb;
"""

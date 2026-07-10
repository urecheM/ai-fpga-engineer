"""Parameterised synthesizable-VHDL generators, each paired with an executable
Python golden-reference model -- driven by architecture decisions.

The generator reads an :class:`ArchDecisions` contract and emits RTL that
reflects it: a binary or one-hot opcode encoding, a shared add/sub datapath, and
optional output registering (a one-stage pipeline). Different decisions therefore
produce meaningfully different hardware with different area/timing, which is what
makes design intent and optimization actually change the design.

Golden-model policy: expected values come from the single spec-derived oracle
in ``ai_fpga_engineer/reference/models.py`` (deduplication). Independence from
the RTL is established by GHDL executing the emitted VHDL against those values
and by the mutation campaign — see docs/CLAIMS.md. ``alu_rtl_emulate`` remains
as a fast in-Python pre-check of the decision-specific datapaths (notably the
shared add/sub arithmetic); the authoritative evidence is the simulator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
import math
import random

from ..core.spec import Specification, Port
from ..core.decisions import ArchDecisions, QoR
from ..reference import models as _refmodels   # single oracle import


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------
@dataclass
class TestPlan:
    kind: str                       # "combinational" | "sequential"
    vectors: list[dict]
    notes: list[str] = field(default_factory=list)


@dataclass
class GeneratedDesign:
    entity: str
    vhdl: str
    kind: str                       # combinational | sequential
    ports: list[Port]
    eval_fn: Callable | None
    run_fn: Callable | None
    default_plan: TestPlan
    resources: dict
    opcode_map: dict = field(default_factory=dict)
    decisions: ArchDecisions = field(default_factory=ArchDecisions)
    latency: int = 0                # output latency in clocks


VHDL_HEADER = """library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
"""


# ===========================================================================
# ALU
# ===========================================================================
# Each op: a VHDL expression building a (WIDTH+1)-bit result vector `res_i`
# (bit WIDTH = carry/borrow, low WIDTH bits = value). The Python golden model
# is bound below from the reference oracle.
_ALU_OPS: dict[str, dict] = {
    "ADD": dict(vhdl="std_logic_vector(resize(unsigned(a), WIDTH+1) + resize(unsigned(b), WIDTH+1))",
                desc="Unsigned addition; carry = carry-out."),
    "SUB": dict(vhdl="std_logic_vector(resize(unsigned(a), WIDTH+1) - resize(unsigned(b), WIDTH+1))",
                desc="Unsigned subtraction; carry bit = borrow (1 when a<b)."),
    "AND": dict(vhdl="'0' & (a and b)", desc="Bitwise AND."),
    "OR":  dict(vhdl="'0' & (a or b)",  desc="Bitwise OR."),
    "XOR": dict(vhdl="'0' & (a xor b)", desc="Bitwise XOR."),
    "NOT": dict(vhdl="'0' & (not a)",   desc="Bitwise NOT of a."),
    "INC": dict(vhdl="std_logic_vector(resize(unsigned(a), WIDTH+1) + 1)",
                desc="a + 1; carry = carry-out."),
    "DEC": dict(vhdl="std_logic_vector(resize(unsigned(a), WIDTH+1) - 1)",
                desc="a - 1; carry = borrow."),
    "SLL": dict(vhdl="a(WIDTH-1) & (a(WIDTH-2 downto 0) & '0')",
                desc="Shift a left 1; carry = bit out."),
    "SRL": dict(vhdl="a(0) & ('0' & a(WIDTH-1 downto 1))",
                desc="Shift a right 1; carry = bit out."),
}

# Golden-model dedup: expected values come from the single spec-derived oracle.
for _op in _ALU_OPS:
    _ALU_OPS[_op]["py"] = (lambda o: lambda a, b, W, m: _refmodels.alu(o, a, b, W))(_op)


def _alu_ops(spec: Specification) -> list[str]:
    ops = [op.name for op in spec.operations] or ["ADD", "SUB", "AND", "OR", "XOR"]
    return [o for o in ops if o in _ALU_OPS]


def _alu_opcodes(ops: list[str], encoding: str) -> tuple[int, dict]:
    """Return (opcode_width, {op: bitstring}) for the chosen encoding."""
    if encoding == "onehot":
        opw = len(ops)
        codes = {op: format(1 << i, f"0{opw}b") for i, op in enumerate(ops)}
    else:
        opw = max(1, math.ceil(math.log2(len(ops))))
        codes = {op: format(i, f"0{opw}b") for i, op in enumerate(ops)}
    return opw, codes


def generate_alu(spec: Specification, d: ArchDecisions) -> GeneratedDesign:
    W = spec.data_width
    mask = (1 << W) - 1
    ops = _alu_ops(spec)
    share = d.share_add_sub and ("ADD" in ops and "SUB" in ops)
    opw, opcode_map = _alu_opcodes(ops, d.opcode_encoding)
    entity = spec.name

    consts = "\n".join(
        f'    constant OP_{op:<4}: std_logic_vector(OPW-1 downto 0) := "{code}";'
        for op, code in opcode_map.items())

    # --- per-op result expression (shared adder reuses precomputed sumv) ---
    def res_expr(op: str) -> str:
        if share and op == "ADD":
            return "std_logic_vector(sumv)"
        if share and op == "SUB":
            # replace the carry bit with the borrow (= not carry)
            return "(not sumv(WIDTH)) & std_logic_vector(sumv(WIDTH-1 downto 0))"
        return _ALU_OPS[op]["vhdl"]

    cases = "\n".join(f"            when OP_{op:<4}=> res_i <= {res_expr(op)};" for op in ops)

    shared_sig = ""
    shared_logic = ""
    if share:
        shared_sig = ("    signal sub_sel : std_logic;\n"
                      "    signal addend  : unsigned(WIDTH downto 0);\n"
                      "    signal cin_v   : unsigned(WIDTH downto 0);\n"
                      "    signal sumv    : unsigned(WIDTH downto 0);\n")
        shared_logic = (
            "    -- shared add/sub datapath: a - b = a + not(b) + 1\n"
            "    sub_sel <= '1' when op = OP_SUB  else '0';\n"
            "    addend  <= resize(unsigned(b), WIDTH+1) when sub_sel = '0'\n"
            "               else resize(unsigned(not b), WIDTH+1);\n"
            "    cin_v   <= (0 => sub_sel, others => '0');\n"
            "    sumv    <= resize(unsigned(a), WIDTH+1) + addend + cin_v;\n\n")

    if d.register_output:
        clk_port = "        clk    : in  std_logic;\n"
        out_drive = """    -- registered outputs (one pipeline stage; latency = 1 clock)
    process(clk)
    begin
        if rising_edge(clk) then
            result <= res_i(WIDTH-1 downto 0);
            carry  <= res_i(WIDTH);
            if res_i(WIDTH-1 downto 0) = std_logic_vector(to_unsigned(0, WIDTH)) then
                zero <= '1';
            else
                zero <= '0';
            end if;
        end if;
    end process;"""
    else:
        clk_port = ""
        out_drive = """    result <= res_i(WIDTH-1 downto 0);
    carry  <= res_i(WIDTH);
    zero   <= '1' when res_i(WIDTH-1 downto 0) = std_logic_vector(to_unsigned(0, WIDTH))
              else '0';"""

    vhdl = f"""{VHDL_HEADER}
-- {spec.title}
-- Auto-generated by AI-FPGA-Engineer.
-- Architecture: {d.label()}. Operations: {", ".join(ops)}.
entity {entity} is
    generic (
        WIDTH : integer := {W};
        OPW   : integer := {opw}
    );
    port (
{clk_port}        a      : in  std_logic_vector(WIDTH-1 downto 0);
        b      : in  std_logic_vector(WIDTH-1 downto 0);
        op     : in  std_logic_vector(OPW-1 downto 0);
        result : out std_logic_vector(WIDTH-1 downto 0);
        carry  : out std_logic;   -- carry-out (add/inc) or borrow (sub/dec)
        zero   : out std_logic    -- asserted when result = 0
    );
end entity {entity};

architecture rtl of {entity} is
{consts}
{shared_sig}    signal res_i : std_logic_vector(WIDTH downto 0);
begin
{shared_logic}    -- combinational function unit
    process(all)
    begin
        case op is
{cases}
            when others => res_i <= (others => '0');
        end case;
    end process;

{out_drive}
end architecture rtl;
"""

    # ---- golden model (semantics; identical for every decision) ----
    def combo(inp: dict) -> dict:
        a, b, opname = inp["a"], inp["b"], inp["op"]
        value, carry = _ALU_OPS[opname]["py"](a, b, W, mask)
        return {"result": value, "carry": carry, "zero": 1 if value == 0 else 0}

    # ---- test plan ----
    edges = sorted({0, 1, 2, mask, mask - 1, mask >> 1, (mask >> 1) + 1})
    vectors = [{"a": a, "b": b, "op": op} for op in ops for a in edges for b in edges]
    rng = random.Random(42)
    vectors += [{"a": rng.randint(0, mask), "b": rng.randint(0, mask), "op": rng.choice(ops)}
                for _ in range(64)]

    ports = _alu_ports(W, opw, d.register_output)
    resources = estimate_alu(W, ops, d)

    if d.register_output:
        plan = TestPlan("sequential", vectors,
                        [f"{len(edges)}x{len(edges)} boundary grid/op + 64 random, clocked (latency 1)"])
        run_fn = lambda seq: [combo(v) for v in seq]  # each vector independent
        return GeneratedDesign(entity, vhdl, "sequential", ports, None, run_fn,
                               plan, resources, opcode_map, d, latency=1)
    plan = TestPlan("combinational", vectors,
                    [f"{len(edges)}x{len(edges)} boundary grid per op + 64 random vectors",
                     "Exhaustive operand sweep available via --exhaustive"])
    return GeneratedDesign(entity, vhdl, "combinational", ports, combo, None,
                           plan, resources, opcode_map, d, latency=0)


def alu_rtl_emulate(d: ArchDecisions, a: int, b: int, opname: str, W: int) -> tuple[int, int]:
    """Mirror the *exact* datapath the emitted VHDL implements, returning
    (result, carry). A fast in-Python pre-check of the decision-specific
    datapaths (especially the shared add/sub arithmetic) against the oracle;
    the authoritative evidence is GHDL executing the RTL. Opcode encoding and
    output registering do not change the computed value, so only the
    shared-adder path needs special handling here."""
    mask = (1 << W) - 1
    share = d.share_add_sub and opname in ("ADD", "SUB")
    if share:
        sub_sel = 1 if opname == "SUB" else 0
        addend = (mask ^ b) if sub_sel else b          # not(b) over W bits when subtracting
        summ = a + addend + sub_sel                    # WIDTH+1-bit sum
        value = summ & mask
        carry_bit = (summ >> W) & 1
        carry = (1 - carry_bit) if sub_sel else carry_bit   # SUB exposes borrow = not carry
        return value, carry
    return _ALU_OPS[opname]["py"](a, b, W, mask)


def alu_exhaustive_plan(spec: Specification) -> TestPlan:
    W = spec.data_width
    ops = _alu_ops(spec)
    n = 1 << W
    vectors = [{"a": a, "b": b, "op": op} for op in ops for a in range(n) for b in range(n)]
    return TestPlan("combinational", vectors, [f"Exhaustive: {len(vectors)} vectors"])


def _alu_ports(W: int, opw: int, registered: bool) -> list[Port]:
    ports = []
    if registered:
        ports.append(Port("clk", "in", 1, "clock"))
    ports += [
        Port("a", "in", W, "data"), Port("b", "in", W, "data"),
        Port("op", "in", opw, "opcode"),
        Port("result", "out", W, "data"), Port("carry", "out", 1, "flag"),
        Port("zero", "out", 1, "flag"),
    ]
    return ports


def estimate_alu(W: int, ops: list[str], d: ArchDecisions) -> dict:
    """Heuristic, decision-aware QoR estimate. Clearly pre-synthesis and used
    only for RANKING; acceptance uses measured numbers when the flow exists.
    Its error band is published by `cli calibrate` (see docs/CLAIMS.md)."""
    n = len(ops)
    arith = [o for o in ops if o in ("ADD", "SUB", "INC", "DEC")]
    share = d.share_add_sub and ("ADD" in ops and "SUB" in ops)
    # adders: one per arithmetic op, unless ADD+SUB are shared into one
    n_adders = len(arith) - (1 if share else 0)
    adder_luts = W * max(0, n_adders)
    mux_luts = int(W * max(1, math.log2(max(2, n))))
    decode_luts = n if d.opcode_encoding == "onehot" else max(1, math.ceil(math.log2(max(2, n))))
    luts = adder_luts + mux_luts + decode_luts
    registers = (W + 2) if d.register_output else 0

    # critical path: arithmetic depth + result-mux depth + opcode decode
    base_cp = 0.6 + (0.18 * W if arith else 0.05 * W) + 0.03 * math.log2(max(2, n))
    if d.opcode_encoding == "onehot":
        base_cp -= 0.04 * math.log2(max(2, n))     # flatter decode
    if d.register_output:
        base_cp *= 0.78                            # output register isolates downstream timing
    cp = round(max(0.2, base_cp), 2)
    return {"luts": luts, "registers": registers, "dsp": 0,
            "critical_path_ns": cp, "fmax_mhz": round(1000.0 / cp, 1)}


# ===========================================================================
# Counter (sequential)
# ===========================================================================
def generate_counter(spec: Specification, d: ArchDecisions) -> GeneratedDesign:
    W = spec.data_width
    mask = (1 << W) - 1
    entity = spec.name
    vhdl = f"""{VHDL_HEADER}
-- {spec.title}
-- Auto-generated by AI-FPGA-Engineer. Synchronous up-counter, active-high sync reset.
entity {entity} is
    generic ( WIDTH : integer := {W} );
    port (
        clk   : in  std_logic;
        rst   : in  std_logic;
        en    : in  std_logic;
        count : out std_logic_vector(WIDTH-1 downto 0);
        tc    : out std_logic
    );
end entity {entity};

architecture rtl of {entity} is
    signal cnt : unsigned(WIDTH-1 downto 0) := (others => '0');
begin
    process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                cnt <= (others => '0');
            elsif en = '1' then
                cnt <= cnt + 1;
            end if;
        end if;
    end process;
    count <= std_logic_vector(cnt);
    tc    <= '1' when cnt = (cnt'range => '1') else '0';
end architecture rtl;
"""

    def run_fn(seq: list[dict]) -> list[dict]:
        cnt, out = 0, []
        for s in seq:
            cnt, tc = _refmodels.counter_step(cnt, s.get("rst", 0), s.get("en", 0), W)
            out.append({"count": cnt, "tc": tc})
        return out

    seq = [{"rst": 1, "en": 0}]
    seq += [{"rst": 0, "en": 1} for _ in range(mask + 3)]
    seq += [{"rst": 0, "en": 0}, {"rst": 0, "en": 0}]
    seq += [{"rst": 0, "en": 1}, {"rst": 1, "en": 0}]
    plan = TestPlan("sequential", seq, ["Reset, full count to wrap-around, hold, resume."])
    ports = [Port("clk", "in", 1, "clock"), Port("rst", "in", 1, "reset"),
             Port("en", "in", 1, "enable"), Port("count", "out", W, "data"),
             Port("tc", "out", 1, "flag")]
    resources = {"luts": W, "registers": W, "dsp": 0,
                 "critical_path_ns": round(0.5 + 0.05 * W, 2),
                 "fmax_mhz": round(1000.0 / (0.5 + 0.05 * W), 1)}
    return GeneratedDesign(entity, vhdl, "sequential", ports, None, run_fn, plan,
                           resources, {}, d, latency=0)


# ===========================================================================
# Register (sequential)
# ===========================================================================
def generate_register(spec: Specification, d: ArchDecisions) -> GeneratedDesign:
    W = spec.data_width
    mask = (1 << W) - 1
    entity = spec.name
    vhdl = f"""{VHDL_HEADER}
-- {spec.title}
-- Auto-generated by AI-FPGA-Engineer. Width-{W} register with enable + sync reset.
entity {entity} is
    generic ( WIDTH : integer := {W} );
    port (
        clk : in  std_logic;
        rst : in  std_logic;
        en  : in  std_logic;
        d   : in  std_logic_vector(WIDTH-1 downto 0);
        q   : out std_logic_vector(WIDTH-1 downto 0)
    );
end entity {entity};

architecture rtl of {entity} is
    signal q_i : std_logic_vector(WIDTH-1 downto 0) := (others => '0');
begin
    process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                q_i <= (others => '0');
            elsif en = '1' then
                q_i <= d;
            end if;
        end if;
    end process;
    q <= q_i;
end architecture rtl;
"""

    def run_fn(seq: list[dict]) -> list[dict]:
        q, out = 0, []
        for s in seq:
            q = _refmodels.register_step(q, s.get("rst", 0), s.get("en", 0),
                                         s.get("d", 0), W)
            out.append({"q": q})
        return out

    rng = random.Random(7)
    seq = [{"rst": 1, "en": 0, "d": 0}]
    for _ in range(12):
        seq.append({"rst": 0, "en": rng.randint(0, 1), "d": rng.randint(0, mask)})
    seq.append({"rst": 1, "en": 0, "d": 0})
    plan = TestPlan("sequential", seq, ["Reset, random load/hold sequence, reset."])
    ports = [Port("clk", "in", 1, "clock"), Port("rst", "in", 1, "reset"),
             Port("en", "in", 1, "enable"), Port("d", "in", W, "data"),
             Port("q", "out", W, "data")]
    resources = {"luts": 0, "registers": W, "dsp": 0,
                 "critical_path_ns": round(0.4 + 0.03 * W, 2),
                 "fmax_mhz": round(1000.0 / (0.4 + 0.03 * W), 1)}
    return GeneratedDesign(entity, vhdl, "sequential", ports, None, run_fn, plan,
                           resources, {}, d, latency=0)


# ===========================================================================
# Comparator (combinational; supports optional output registering)
# ===========================================================================
def generate_comparator(spec: Specification, d: ArchDecisions) -> GeneratedDesign:
    W = spec.data_width
    mask = (1 << W) - 1
    entity = spec.name
    if d.register_output:
        clk_port = "        clk : in  std_logic;\n"
        body = """    signal gt_i, eq_i, lt_i : std_logic;
begin
    gt_i <= '1' when unsigned(a) > unsigned(b) else '0';
    eq_i <= '1' when unsigned(a) = unsigned(b) else '0';
    lt_i <= '1' when unsigned(a) < unsigned(b) else '0';
    process(clk)
    begin
        if rising_edge(clk) then
            gt <= gt_i; eq <= eq_i; lt <= lt_i;
        end if;
    end process;"""
    else:
        clk_port = ""
        body = """begin
    gt <= '1' when unsigned(a) > unsigned(b) else '0';
    eq <= '1' when unsigned(a) = unsigned(b) else '0';
    lt <= '1' when unsigned(a) < unsigned(b) else '0';"""
    vhdl = f"""{VHDL_HEADER}
-- {spec.title}
-- Auto-generated by AI-FPGA-Engineer. Unsigned magnitude comparator ({d.label()}).
entity {entity} is
    generic ( WIDTH : integer := {W} );
    port (
{clk_port}        a  : in  std_logic_vector(WIDTH-1 downto 0);
        b  : in  std_logic_vector(WIDTH-1 downto 0);
        gt : out std_logic;
        eq : out std_logic;
        lt : out std_logic
    );
end entity {entity};

architecture rtl of {entity} is
{body}
end architecture rtl;
"""

    def combo(inp: dict) -> dict:
        gt, eq, lt = _refmodels.comparator(inp["a"], inp["b"])
        return {"gt": gt, "eq": eq, "lt": lt}

    edges = sorted({0, 1, mask, mask >> 1, (mask >> 1) + 1})
    vectors = [{"a": a, "b": b} for a in edges for b in edges]
    rng = random.Random(11)
    vectors += [{"a": rng.randint(0, mask), "b": rng.randint(0, mask)} for _ in range(40)]
    ports = []
    if d.register_output:
        ports.append(Port("clk", "in", 1, "clock"))
    ports += [Port("a", "in", W, "data"), Port("b", "in", W, "data"),
              Port("gt", "out", 1, "flag"), Port("eq", "out", 1, "flag"),
              Port("lt", "out", 1, "flag")]
    cp = round(0.5 + 0.12 * W, 2)
    if d.register_output:
        cp = round(cp * 0.8, 2)
    resources = {"luts": 2 * W, "registers": 3 if d.register_output else 0, "dsp": 0,
                 "critical_path_ns": cp, "fmax_mhz": round(1000.0 / cp, 1)}
    if d.register_output:
        plan = TestPlan("sequential", vectors, ["Boundary grid + 40 random, clocked (latency 1)."])
        return GeneratedDesign(entity, vhdl, "sequential", ports, None,
                               lambda seq: [combo(v) for v in seq], plan, resources,
                               {}, d, latency=1)
    plan = TestPlan("combinational", vectors, ["Boundary grid + 40 random vectors."])
    return GeneratedDesign(entity, vhdl, "combinational", ports, combo, None, plan,
                           resources, {}, d, latency=0)


# ===========================================================================
# Dispatch
# ===========================================================================
_GENERATORS: dict[str, Callable[[Specification, ArchDecisions], GeneratedDesign]] = {
    "alu": generate_alu,
    "counter": generate_counter,
    "register": generate_register,
    "comparator": generate_comparator,
}


def supported_classes() -> list[str]:
    return sorted(_GENERATORS)


def generate(spec: Specification, decisions: ArchDecisions | None = None) -> GeneratedDesign:
    if spec.design_class not in _GENERATORS:
        raise NotImplementedError(
            f"design_class '{spec.design_class}' not in generation library "
            f"({', '.join(supported_classes())}). Unknown requests are reported, "
            "not guessed at.")
    return _GENERATORS[spec.design_class](spec, decisions or ArchDecisions())


def candidate_decisions(spec: Specification) -> list[ArchDecisions]:
    """Enumerate the architecture design space for a class (for DSE)."""
    if spec.design_class == "alu":
        ops = _alu_ops(spec)
        cands = [
            ArchDecisions("binary", False, False),
            ArchDecisions("onehot", False, False),
            ArchDecisions("binary", True, False),    # registered
            ArchDecisions("onehot", True, False),
        ]
        if "ADD" in ops and "SUB" in ops:
            cands.append(ArchDecisions("binary", False, True))   # shared add/sub
            cands.append(ArchDecisions("binary", True, True))
        return cands
    if spec.design_class == "comparator":
        return [ArchDecisions(register_output=False), ArchDecisions(register_output=True)]
    # counter / register: already sequential; single architecture
    return [ArchDecisions()]


def estimate(spec: Specification, decisions: ArchDecisions) -> QoR:
    """QoR estimate for a class+decisions without fully generating (cheap DSE)."""
    if spec.design_class == "alu":
        r = estimate_alu(spec.data_width, _alu_ops(spec), decisions)
    else:
        r = generate(spec, decisions).resources
    return QoR(r["luts"], r["registers"], r.get("dsp", 0),
               r["critical_path_ns"], r["fmax_mhz"], "estimated")

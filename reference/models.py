""" establishing correctness:
1. The testbench embeds expected values produced by THIS module.
2. GHDL compiles and executes the *actual emitted VHDL* against those values,
   so the RTL — an independent artifact — is checked against the oracle.
3. The mutation campaign (``python -m ai_fpga_engineer.cli mutation-campaign``)
   seeds defects into the RTL text and demonstrates the flow detects them,
   which is the evidence that step 2 has real discriminating power.
from __future__ import annotations """

ALU_OP_NAMES = ("ADD", "SUB", "AND", "OR", "XOR", "NOT", "INC", "DEC", "SLL", "SRL")


def alu(op: str, a: int, b: int, width: int) -> tuple[int, int]:
    """Return (result, carry) for one ALU operation."""
    mask = (1 << width) - 1
    a &= mask
    b &= mask
    if op == "ADD":
        s = a + b
        return s & mask, (s >> width) & 1
    if op == "SUB":
        return (a - b) & mask, 1 if a < b else 0
    if op == "AND":
        return a & b, 0
    if op == "OR":
        return a | b, 0
    if op == "XOR":
        return a ^ b, 0
    if op == "NOT":
        return (~a) & mask, 0
    if op == "INC":
        s = a + 1
        return s & mask, (s >> width) & 1
    if op == "DEC":
        return (a - 1) & mask, 1 if a == 0 else 0
    if op == "SLL":
        return (a << 1) & mask, (a >> (width - 1)) & 1
    if op == "SRL":
        return a >> 1, a & 1
    raise ValueError(f"unknown ALU op {op!r}")
  def alu_zero(result: int) -> int:
    return 1 if result == 0 else 0


def comparator(a: int, b: int) -> tuple[int, int, int]:
    """Return (gt, eq, lt)."""
    return int(a > b), int(a == b), int(a < b)


def counter_step(count: int, rst: int, en: int, width: int) -> tuple[int, int]:
    """Advance the counter one clock; return (new_count, tc)."""
    mask = (1 << width) - 1
    if rst:
        count = 0
    elif en:
        count = (count + 1) & mask
    return count, 1 if count == mask else 0


def register_step(q: int, rst: int, en: int, d: int, width: int) -> int:
    """Advance the register one clock; return new q."""
    mask = (1 << width) - 1
    if rst:
        return 0
    if en:
        return d & mask
    return q

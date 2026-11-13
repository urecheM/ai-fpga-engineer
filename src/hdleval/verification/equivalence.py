"""Formal equivalence of a candidate against the reference, via a miter + SymbiYosys.

The miter instantiates the candidate (entity ``E``) and the reference (renamed
``E_ref``), drives both with the same free inputs every cycle, and asserts (in
PSL) that every output is equal. SymbiYosys then either proves the assertion
(``abc pdr``: unbounded, for every reachable state) or, if the proof does not
close in time, checks it to a bounded depth (``smtbmc``).

Conventions, so the result has a precise meaning:

* reset: if the design has a ``rst``/``reset`` (``*_n`` = active-low) input it
  is assumed active in the first cycle; outputs are compared from cycle 1 on;
* registers without an initial value start at 0 in **both** designs
  (``setundef -init -zero``), so uninitialised state cannot cause a spurious
  difference; a candidate that differs from the reference only in the reset
  value of an unreset register is therefore treated as equivalent;
* clocks are modelled (``multiclock on``), so a design clocked on the wrong
  edge is distinguishable from the reference;
* statuses: ``proven`` | ``bmc_pass`` (no difference within ``depth`` cycles)
  | ``fail`` (counterexample, or a combinational loop) | ``error`` | ``skipped``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from ..parsing.ports import PortSig, parse_ports

CLOCK_NAMES = {"clk", "clock"}
RESET_NAMES = {"rst", "reset", "rst_n", "reset_n"}


@dataclass(frozen=True)
class EquivResult:
    status: str  # proven | bmc_pass | fail | error | skipped
    depth: int = 0
    detail: str = ""
    log_tail: str = field(default="", repr=False)

    @property
    def ok(self) -> bool:
        return self.status in ("proven", "bmc_pass")


def rename_entity(vhdl: str, entity: str, new: str) -> str:
    """Rename entity ``entity`` to ``new`` in its declaration, end and architecture."""
    e = re.escape(entity)
    out = re.sub(rf"\bentity\s+{e}\s+is\b", f"entity {new} is", vhdl, flags=re.I)
    out = re.sub(rf"\bend\s+entity\s+{e}\b", f"end entity {new}", out, flags=re.I)
    out = re.sub(rf"\bend\s+{e}\s*;", f"end {new};", out, flags=re.I)
    out = re.sub(rf"\b(architecture\s+\w+\s+of\s+){e}\b", rf"\g<1>{new}", out, flags=re.I)
    return out


def miter_vhdl(entity: str, ports: list[PortSig]) -> str:
    ins = [p for p in ports if p.direction == "in" and p.name not in CLOCK_NAMES]
    outs = [p for p in ports if p.direction == "out"]
    clk = next((p.name for p in ports if p.name in CLOCK_NAMES), None)
    rst = next((p for p in ins if p.name in RESET_NAMES), None)

    def typ(p: PortSig) -> str:
        return f"std_logic_vector({(p.width or 1) - 1} downto 0)" if p.is_vector else "std_logic"

    port_decl = ["clk : in std_logic"] + [f"{p.name} : in {typ(p)}" for p in ins]
    sigs = "\n".join(f"  signal c_{p.name}, r_{p.name} : {typ(p)};" for p in outs)

    def assoc(prefix: str) -> str:
        parts = [f"{clk} => clk"] if clk else []
        parts += [f"{p.name} => {p.name}" for p in ins]
        parts += [f"{p.name} => {prefix}_{p.name}" for p in outs]
        return ", ".join(parts)

    equal = " and ".join(f"c_{p.name} = r_{p.name}" for p in outs) or "true"
    reset_assume = ""
    if rst is not None:
        active = "'0'" if rst.name.endswith("_n") else "'1'"
        reset_assume = (
            f"  -- psl assume_reset : assume always (first = '1' -> {rst.name} = {active});\n"
        )
    return f"""library ieee; use ieee.std_logic_1164.all;
entity miter is
  port ({"; ".join(port_decl)});
end entity;
architecture formal of miter is
{sigs}
  signal first : std_logic := '1';
  signal same  : std_logic;
begin
  cand : entity work.{entity} port map ({assoc("c")});
  ref  : entity work.{entity}_ref port map ({assoc("r")});
  process (clk) begin
    if rising_edge(clk) then first <= '0'; end if;
  end process;
  same <= '1' when ({equal}) else '0';
  -- psl default clock is rising_edge(clk);
{reset_assume}  -- psl outputs_equal : assert always (first = '0' -> same = '1');
end architecture;
"""


def _sby(mode: str, depth: int, engine: str, timeout_s: int) -> str:
    return f"""[options]
mode {mode}
multiclock on
depth {depth}
timeout {timeout_s}

[engines]
{engine}

[script]
plugin -i ghdl
ghdl --std=08 -fpsl candidate.vhd reference.vhd miter.vhd -e miter
prep -top miter
memory_map
opt_clean
setundef -init -zero
setundef -undriven -anyseq

[files]
candidate.vhd
reference.vhd
miter.vhd
"""


def _run_sby(d: Path, name: str, timeout_s: int) -> tuple[str, str]:
    try:
        r = subprocess.run(
            ["sby", "-f", f"{name}.sby"],
            cwd=d,
            capture_output=True,
            text=True,
            timeout=timeout_s + 60,
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT", ""
    out = r.stdout + r.stderr
    m = re.search(r"DONE \((\w+),", out)
    status = m.group(1) if m else "ERROR"
    if status == "ERROR" and "found logic loop" in out:
        status = "LOOP"  # combinational loop, e.g. a latch inferred by a missing branch
    return status, out[-1500:]


def check_equivalence(
    candidate: str,
    reference: str,
    entity: str,
    *,
    sequential_depth: int = 24,
    prove_timeout_s: int = 120,
) -> EquivResult:
    if not shutil.which("sby"):
        return EquivResult("skipped", detail="sby not installed")
    ports = parse_ports(reference, entity)
    if not ports or any(p.width is None for p in ports):
        return EquivResult("skipped", detail="could not parse reference ports")
    sequential = any(p.name in CLOCK_NAMES for p in ports)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "candidate.vhd").write_text(candidate)
        (d / "reference.vhd").write_text(rename_entity(reference, entity, f"{entity}_ref"))
        (d / "miter.vhd").write_text(miter_vhdl(entity, ports))
        # unbounded proof first (PDR finds the inductive invariant itself)
        (d / "prove.sby").write_text(_sby("prove", 1, "abc pdr", prove_timeout_s))
        status, log = _run_sby(d, "prove", prove_timeout_s)
        if status == "LOOP":
            return EquivResult("fail", detail="combinational loop (inferred latch)", log_tail=log)
        if status == "PASS":
            return EquivResult("proven", log_tail=log)
        if status == "FAIL":
            return EquivResult("fail", detail="counterexample found", log_tail=log)
        if not sequential:
            return EquivResult("error", detail=f"prove returned {status}", log_tail=log)
        # proof did not close: bounded check instead, reported as such
        (d / "bmc.sby").write_text(_sby("bmc", sequential_depth, "smtbmc yices", 600))
        status, log = _run_sby(d, "bmc", 600)
        if status == "PASS":
            return EquivResult("bmc_pass", depth=sequential_depth, log_tail=log)
        if status == "FAIL":
            return EquivResult("fail", depth=sequential_depth, log_tail=log)
        return EquivResult("error", detail=f"bmc returned {status}", log_tail=log)

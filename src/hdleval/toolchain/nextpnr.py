"""Measured timing via place-and-route on iCE40 (Yosys + nextpnr-ice40).

The design is wrapped in a timing harness: a serial shift register drives all
DUT inputs and all DUT outputs are registered, so (a) the design fits the
package pins regardless of its width and (b) nextpnr times the DUT's logic as a
register-to-register path. The achieved Fmax nextpnr reports is a measurement
for that device, package and seed; nothing here is estimated.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from ..parsing.ports import PortSig, parse_ports
from .detect import ToolResult, detect

DEVICE = "up5k"
PACKAGE = "sg48"
SEED = 1
FREQ_TARGET_MHZ = 40  # placement target only; the achieved Fmax is reported
CLOCK_NAMES = {"clk", "clock"}


def timing_harness(entity: str, ports: list[PortSig]) -> str:
    ins = [p for p in ports if p.direction == "in" and p.name not in CLOCK_NAMES]
    outs = [p for p in ports if p.direction == "out"]
    has_clk = any(p.name in CLOCK_NAMES for p in ports)
    nin = sum(p.width or 1 for p in ins)
    nout = sum(p.width or 1 for p in outs)
    decls, drive, collect, assoc = [], [], [], []
    if has_clk:
        assoc.append(next(f"{p.name} => clk" for p in ports if p.name in CLOCK_NAMES))
    bit = 0
    for p in ins:
        w = p.width or 1
        if p.is_vector:
            decls.append(f"  signal s_{p.name} : std_logic_vector({w - 1} downto 0);")
            drive.append(f"  s_{p.name} <= sr({bit + w - 1} downto {bit});")
        else:
            decls.append(f"  signal s_{p.name} : std_logic;")
            drive.append(f"  s_{p.name} <= sr({bit});")
        assoc.append(f"{p.name} => s_{p.name}")
        bit += w
    bit = 0
    for p in outs:
        w = p.width or 1
        if p.is_vector:
            decls.append(f"  signal s_{p.name} : std_logic_vector({w - 1} downto 0);")
            collect.append(f"  obus({bit + w - 1} downto {bit}) <= s_{p.name};")
        else:
            decls.append(f"  signal s_{p.name} : std_logic;")
            collect.append(f"  obus({bit}) <= s_{p.name};")
        assoc.append(f"{p.name} => s_{p.name}")
        bit += w
    nl = "\n"
    return f"""library ieee; use ieee.std_logic_1164.all;
entity {entity}_timed is
  port (clk, si : in std_logic; so : out std_logic);
end entity;
architecture harness of {entity}_timed is
  signal sr   : std_logic_vector({max(nin, 2) - 1} downto 0) := (others => '0');
  signal obus : std_logic_vector({max(nout, 1) - 1} downto 0);
  signal oreg : std_logic_vector({max(nout, 1) - 1} downto 0) := (others => '0');
{nl.join(decls)}
begin
  process(clk) begin
    if rising_edge(clk) then
      sr   <= sr(sr'high - 1 downto 0) & si;
      oreg <= obus;
    end if;
  end process;
{nl.join(drive)}
  dut : entity work.{entity} port map ({", ".join(assoc)});
{nl.join(collect)}
  so <= xor oreg;
end architecture;
"""


def _fmax(report: Path) -> float | None:
    try:
        data = json.loads(report.read_text())
    except (OSError, ValueError):
        return None
    achieved = [
        v["achieved"]
        for v in (data.get("fmax") or {}).values()
        if isinstance(v, dict) and v.get("achieved")
    ]
    return min(achieved) if achieved else None


def place_and_route(vhdl: str, entity: str, *, timeout: float = 600.0) -> ToolResult:
    """Synthesize + place-and-route on iCE40 UP5K; metrics carry the measured Fmax."""
    tc = detect()
    if not (tc.has("yosys") and tc.ghdl_plugin and tc.has("nextpnr-ice40")):
        return ToolResult(status="skipped", stderr="yosys/ghdl-plugin/nextpnr-ice40 missing")
    ports = parse_ports(vhdl, entity)
    if not ports or any(p.width is None for p in ports):
        return ToolResult(status="skipped", stderr="could not parse literal port widths")
    with tempfile.TemporaryDirectory() as d:
        dd = Path(d)
        (dd / "design.vhd").write_text(vhdl)
        (dd / "timed.vhd").write_text(timing_harness(entity, ports))
        script = (
            "plugin -i ghdl; ghdl --std=08 design.vhd timed.vhd "
            f"-e {entity}_timed; synth_ice40 -top {entity}_timed -json net.json"
        )
        try:
            y = subprocess.run(
                ["yosys", "-q", "-p", script],
                cwd=d,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if y.returncode != 0:
                return ToolResult(status="fail", stderr=y.stderr[-800:])
            n = subprocess.run(
                [
                    "nextpnr-ice40",
                    f"--{DEVICE}",
                    "--package",
                    PACKAGE,
                    "--json",
                    "net.json",
                    "--report",
                    "report.json",
                    "--pcf-allow-unconstrained",
                    "--freq",
                    str(FREQ_TARGET_MHZ),
                    "--seed",
                    str(SEED),
                ],
                cwd=d,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(status="fail", stderr="place-and-route timeout")
        if n.returncode != 0:
            return ToolResult(status="fail", stderr=n.stderr[-800:])
        fmax = _fmax(dd / "report.json")
        if fmax is None:
            return ToolResult(status="fail", stderr="no fmax in nextpnr report")
        return ToolResult(
            status="ok",
            metrics={"fmax_mhz": round(fmax, 2)},
            stdout=f"{DEVICE}/{PACKAGE} seed {SEED}",
        )

#!/usr/bin/env python3
"""For every benchmark in a suite w/ no hand-written testbench:
1. parse reference entity ports
2. generate seeded pseudo-random stimulus
3. simulate reference under GHDL with a recorder testbench that writes every output on every cycle
4. emit ``golden_tb.vhd``
5. re-run reference against the new testbench
Usage: python scripts/build_golden_vectors.py [--suite v1] [--only ID ...] [--force]
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hdleval.benchmarks.loader import load_suite, reference_hdl  # noqa: E402
from hdleval.parsing.ports import PortSig, parse_ports  # noqa: E402

CLOCK_NAMES = {"clk", "clock"}
RESET_NAMES = {"rst", "reset", "rst_n", "reset_n"}

DEFAULTS = {
    "cycles": 400,
    "comb_vectors": 512,
    "hold": 0.5,
    "reset_cycles": 2,
    "reset_rate": 0.01,
    "seed": 20260707,
}

# Per-benchmark stimulus tuning
OVERRIDES: dict[str, dict] = {
    "ctrl_debounce": {"hold": {"din": 0.93}},
    "ctrl_pwm": {"cycles": 1200, "hold": {"duty": 0.995}},
    "fsm_traffic": {"hold": {"tick": 0.3}},
    "comm_i2c_ctrl": {"hold": {"start": 0.9, "data": 0.9}},
    "mem_fifo": {"cycles": 600},
    "mem_regfile": {"narrow": {"ra1": 3, "ra2": 3, "wa": 3}},
    "mem_sync_ram": {"narrow": {"addr": 3}},
    "dsp_fir4": {"hold": {"x": 0.2}},
    "dsp_movavg": {"hold": {"x": 0.2}},
}


def _bits(rng: random.Random, width: int, narrow: int | None) -> str:
    n = min(width, narrow) if narrow else width
    v = rng.getrandbits(n) if n else 0
    return format(v, f"0{width}b")


def _stimulus(ports: list[PortSig], cfg: dict, clocked: bool) -> list[dict[str, str]]:
    rng = random.Random(cfg["seed"])
    ins = [p for p in ports if p.direction == "in" and p.name not in CLOCK_NAMES]
    hold = cfg.get("hold", {}) if isinstance(cfg.get("hold"), dict) else {}
    base_hold = cfg["hold"] if isinstance(cfg.get("hold"), float) else DEFAULTS["hold"]
    narrow = cfg.get("narrow", {})
    p_one = cfg.get("p_one", {})
    phases = int(cfg.get("phases", 1))
    vecs: list[dict[str, str]] = []
    if not clocked:
        for fill in ("0", "1"):
            vecs.append({p.name: fill * (p.width or 1) for p in ins})
        n = cfg["comb_vectors"]
    else:
        n = cfg["cycles"]
    prev = {p.name: "0" * (p.width or 1) for p in ins}
    for i in range(n):
        cur = {}
        for p in ins:
            w = p.width or 1
            if p.name in RESET_NAMES and clocked:
                active = "0" if p.name.endswith("_n") else "1"
                idle = "1" if active == "0" else "0"
                if i < cfg["reset_cycles"] or rng.random() < cfg["reset_rate"]:
                    cur[p.name] = active
                else:
                    cur[p.name] = idle
            elif clocked and rng.random() < hold.get(p.name, base_hold):
                cur[p.name] = prev[p.name]
            elif p.name in p_one and w == 1:
                prob = p_one[p.name]
                if (i * phases // n) % 2 == 1:
                    prob = 1.0 - prob
                cur[p.name] = "1" if rng.random() < prob else "0"
            else:
                cur[p.name] = _bits(rng, w, narrow.get(p.name))
        vecs.append(cur)
        prev = cur
    return vecs


def _decl(p: PortSig) -> str:
    if p.is_vector:
        return f"std_logic_vector({(p.width or 1) - 1} downto 0)"
    return "std_logic"


def _lit(p: PortSig, bits: str) -> str:
    return f'"{bits}"' if p.is_vector else f"'{bits}'"


def _tb(entity: str, ports: list[PortSig], vecs, expected, clocked: bool, ignore) -> str:
    """Recorder testbench if ``expected`` is None, checking testbench otherwise."""
    ins = [p for p in ports if p.direction == "in" and p.name not in CLOCK_NAMES]
    outs = [p for p in ports if p.direction == "out" and p.name not in ignore]
    tb = f"{entity}_golden_tb"
    sigs = "\n".join(f"  signal s_{p.name} : {_decl(p)};" for p in ports)
    assoc = ", ".join(f"{p.name} => s_{p.name}" for p in ports)
    n = len(vecs)
    in_rows = []
    for v in vecs:
        in_rows.append('"' + "".join(v[p.name] for p in ins) + '"')
    in_w = sum(p.width or 1 for p in ins)
    out_w = sum(p.width or 1 for p in outs)
    drive, pos = [], 0
    for p in ins:
        w = p.width or 1
        if p.is_vector:
            drive.append(f"      s_{p.name} <= stim(i)({pos + 1} to {pos + w});")
        else:
            drive.append(f"      s_{p.name} <= stim(i)({pos + 1});")
        pos += w
    gather, pos = [], 1
    for p in outs:
        w = p.width or 1
        if p.is_vector:
            gather.append(f"      got({pos} to {pos + w - 1}) := s_{p.name};")
        else:
            gather.append(f"      got({pos}) := s_{p.name};")
        pos += w
    settle = (
        "      wait until rising_edge(clk_i);\n      wait for 1 ns;\n"
        if clocked
        else "      wait for 5 ns;\n"
    )
    clk_gen = "  clk_i <= not clk_i after 5 ns when not done else clk_i;\n" if clocked else ""
    clk_assoc = next((f"s_{p.name} <= clk_i;" for p in ports if p.name in CLOCK_NAMES), "")
    header = f"""-- GENERATED by scripts/build_golden_vectors.py -- do not edit by hand.
library ieee; use ieee.std_logic_1164.all; use std.textio.all;
entity {tb} is end entity;
architecture sim of {tb} is
{sigs}
  signal clk_i : std_logic := '0';
  signal done  : boolean := false;
  type stim_t is array (0 to {n - 1}) of std_logic_vector(1 to {max(in_w, 1)});
  constant stim : stim_t := (
    {("," + chr(10) + "    ").join(in_rows) if in_rows and in_w else "others => (others => '0')"});
"""
    if expected is not None:
        exp_rows = ",\n    ".join('"' + e + '"' for e in expected)
        header += f"""  type exp_t is array (0 to {n - 1}) of std_logic_vector(1 to {max(out_w, 1)});
  constant expv : exp_t := (
    {exp_rows});
"""
    body = f"""begin
  dut : entity work.{entity} port map ({assoc});
{clk_gen}  {clk_assoc}
  process
    variable l : line;
    variable got : std_logic_vector(1 to {max(out_w, 1)});
    variable errors : natural := 0;
"""
    if expected is None:
        body += '    file f : text open write_mode is "golden_out.txt";\n'
    pre = "      wait until falling_edge(clk_i);\n      wait for 2 ns;\n" if clocked else ""
    body += "  begin\n    for i in stim'range loop\n" + pre + "\n".join(drive) + "\n" + settle
    body += "\n".join(gather) + "\n"
    if expected is None:
        body += "      write(l, to_string(got)); writeline(f, l);\n"
    else:
        body += """      for b in got'range loop
        if expv(i)(b) /= '-' and got(b) /= expv(i)(b) then
          errors := errors + 1;
          if errors <= 10 then
            report "MISMATCH vector " & integer'image(i) & " bit " & integer'image(b)
              & " expected " & std_logic'image(expv(i)(b))
              & " got " & std_logic'image(got(b)) severity warning;
          end if;
        end if;
      end loop;
"""
    body += "    end loop;\n    done <= true;\n"
    if expected is not None:
        body += """    assert errors = 0
      report integer'image(errors) & " output bit(s) differ from the golden vectors"
      severity error;
    if errors = 0 then report "GOLDEN_PASS" severity note; end if;
"""
    body += "    wait;\n  end process;\nend architecture;\n"
    return header + body


def _ghdl(d: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["ghdl", *args], cwd=d, capture_output=True, text=True, timeout=300)


def _run(design: str, tb: str, tb_entity: str) -> tuple[subprocess.CompletedProcess, Path]:
    d = Path(tempfile.mkdtemp())
    (d / "design.vhd").write_text(design)
    (d / "tb.vhd").write_text(tb)
    for step in (["-a", "--std=08", "design.vhd", "tb.vhd"], ["-e", "--std=08", tb_entity]):
        r = _ghdl(d, *step)
        if r.returncode:
            return r, d
    return _ghdl(d, "-r", "--std=08", tb_entity, "--assert-level=error"), d


def build_one(b, root: Path | None, force: bool) -> str:
    if b.testbench_path and b.testbench_path != "golden_tb.vhd":
        return "hand-written testbench kept"
    bdir = ROOT / "benchmarks" / (b.suite or f"v{b.version.split('.')[0]}") / b.id
    out = bdir / "golden_tb.vhd"
    if out.exists() and not force:
        return "exists (use --force to regenerate)"
    ref = reference_hdl(b, root)
    ports = parse_ports(ref, b.entity)
    if not ports or any(p.width is None for p in ports):
        return "SKIP: could not parse literal port widths"
    clocked = any(p.name in CLOCK_NAMES for p in ports)
    import yaml
    own = (yaml.safe_load((bdir / "benchmark.yaml").read_text()) or {}).get("golden", {})
    cfg = {**DEFAULTS, **OVERRIDES.get(b.id, {}), **own}
    ignore = set(cfg.get("ignore", []))
    vecs = _stimulus(ports, cfg, clocked)
    tb_entity = f"{b.entity}_golden_tb"

    rec, d = _run(ref, _tb(b.entity, ports, vecs, None, clocked, ignore), tb_entity)
    if rec.returncode:
        return f"FAIL recording: {rec.stderr[-400:]}"
    raw = (d / "golden_out.txt").read_text().split()
    shutil.rmtree(d, ignore_errors=True)
    expected = ["".join(c if c in "01ZHL" else "-" for c in row) for row in raw]
    tb_text = _tb(b.entity, ports, vecs, expected, clocked, ignore)

    chk, d = _run(ref, tb_text, tb_entity)
    shutil.rmtree(d, ignore_errors=True)
    if chk.returncode or "GOLDEN_PASS" not in chk.stdout + chk.stderr:
        return f"FAIL self-check: {chk.stderr[-400:]}"
    out.write_text(tb_text)
    dont_care = sum(row.count("-") for row in expected)
    total = sum(len(row) for row in expected)
    (bdir / "golden.json").write_text(
        json.dumps(
            {
                "vectors": len(vecs),
                "clocked": clocked,
                "stimulus": cfg,
                "dont_care_fraction": round(dont_care / max(total, 1), 4),
            },
            indent=2,
        )
        + "\n"
    )
    return f"ok ({len(vecs)} vectors, {dont_care}/{total} don't-care bits)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="v1")
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--benchmarks-root", default=None)
    args = ap.parse_args()
    if not shutil.which("ghdl"):
        print("ghdl not installed: keeping existing golden testbenches", file=sys.stderr)
        return 0
    failed = False
    for b in load_suite(args.suite, args.benchmarks_root):
        if args.only and b.id not in args.only:
            continue
        msg = build_one(b, args.benchmarks_root, args.force)
        failed |= msg.startswith("FAIL")
        print(f"{b.id:20s} {msg}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
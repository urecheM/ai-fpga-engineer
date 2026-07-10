"""Synthesis stage.

Priority order, each honestly labelled in the QoR ``source`` field:

1. **Full measured flow** (yosys + GHDL plugin + nextpnr-ice40): real SB_LUT4 /
   SB_DFF counts and the *achieved Fmax* from place-and-route on an iCE40 UP5K
   — see :mod:`ai_fpga_engineer.sim.pnr`. This is the number the QoR loop and
   the report should trust.
2. **Yosys only**: generic LUT4 mapping for representative cell counts. No
   timing — Fmax is reported as 0.0 and labelled ``yosys-counts-only`` rather
   than pretending.
3. **No tools**: a runnable flow is emitted and the heuristic estimate is used,
   labelled ``estimated``. With ``AIFPGA_REQUIRE_TOOLS=1`` (CI) this path is a
   hard failure instead of a silent fallback.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

from ..agents.base import Agent
from ..core.project import Project
from ..core.decisions import QoR
from ..core import toolchain
from ..hdl.library import GeneratedDesign
from . import pnr


@dataclass
class SynthResult:
    ran: bool
    backend: str                 # "nextpnr-ice40" | "yosys-counts-only" | "flow-emitted"
    qor: QoR | None = None       # real numbers if a tool ran
    flow_path: str = ""
    log: str = ""


class SynthAgent(Agent):
    name = "synthesis"

    def run(self, project: Project, design: GeneratedDesign,
            estimate: QoR | None = None) -> SynthResult:
        flow_rel = f"synth/{design.entity}_synth.ys"
        project.write(flow_rel, self._yosys_script(design), "synth_script")
        project.write("synth/README.md", self._readme(design), "synth_readme")

        # 1. full measured flow
        ok, why = pnr.available()
        if ok:
            res = pnr.run_ice40(project, design)
            if res.ran and res.qor is not None:
                self.log(project, f"nextpnr-ice40 ({pnr.DEVICE}): {res.qor.luts} LUT4, "
                                  f"{res.qor.registers} FF, Fmax {res.qor.fmax_mhz} MHz "
                                  f"(measured, seed {pnr.SEED})", "success")
                return SynthResult(True, "nextpnr-ice40", res.qor, flow_rel, res.log)
            self.log(project, f"place-and-route failed: {res.reason}", "error")
            if toolchain.require_tools():
                raise RuntimeError(f"AIFPGA_REQUIRE_TOOLS=1 but PnR failed: {res.reason}")

        # 2. yosys-only counts
        if toolchain.detect().present.get("yosys") and toolchain.detect().ghdl_plugin:
            res = self._run_yosys_counts(project, design)
            if res is not None:
                return res

        # 3. emitted flow only
        msg = (f"no usable synthesis flow ({why if not ok else 'yosys counts failed'}); "
               f"emitted runnable flow under synth/")
        if toolchain.require_tools():
            raise RuntimeError(f"AIFPGA_REQUIRE_TOOLS=1: {msg}")
        self.log(project, msg, "warn")
        if estimate is not None:
            self.log(project, f"falling back to heuristic estimate: {estimate.luts} LUTs, "
                              f"{estimate.registers} regs, Fmax≈{estimate.fmax_mhz} MHz "
                              f"(source={estimate.source})")
        return SynthResult(False, "flow-emitted", None, flow_rel)

    # ------------------------------------------------------------------
    def _run_yosys_counts(self, project, design) -> SynthResult | None:
        e = design.entity
        ys = (f"plugin -i ghdl; ghdl --std=08 rtl/{e}.vhd -e {e}; "
              f"hierarchy -top {e}; proc; opt; fsm; opt; memory; opt; "
              f"techmap; opt; abc -lut 4; clean; stat")
        try:
            out = subprocess.run(["yosys", "-p", ys], cwd=str(project.root),
                                 capture_output=True, text=True, timeout=300)
        except Exception as exc:
            self.log(project, f"yosys invocation failed ({exc})", "warn")
            return None
        log = out.stdout + out.stderr
        if out.returncode != 0:
            self.log(project, "yosys generic mapping failed (see synth log)", "warn")
            return None
        luts = self._grep_max(log, r"\$lut\s+(\d+)")
        ffs = self._grep_sum(log, r"\$_DFF\w*_\s+(\d+)")
        qor = QoR(luts or 0, ffs or 0, 0, 0.0, 0.0, "yosys-counts-only")
        self.log(project, f"yosys generic mapping: {qor.luts} LUT4-equiv, {qor.registers} FFs "
                          "(cell counts only — no timing; install nextpnr-ice40 for Fmax)",
                 "success")
        return SynthResult(True, "yosys-counts-only", qor,
                           f"synth/{e}_synth.ys", log)

    @staticmethod
    def _grep_max(log: str, pattern: str) -> int | None:
        m = re.findall(pattern, log, re.I)
        return max(int(x) for x in m) if m else None

    @staticmethod
    def _grep_sum(log: str, pattern: str) -> int | None:
        m = re.findall(pattern, log, re.I)
        return sum(int(x) for x in m) if m else None

    def _yosys_script(self, design: GeneratedDesign) -> str:
        e = design.entity
        return f"""# Yosys/nextpnr flow for {e} (generated by AI FPGA Engineer).
# Run from the project root. Requires the OSS CAD Suite (yosys with the GHDL
# plugin, nextpnr-ice40):
#   yosys -p 'plugin -i ghdl' -s synth/{e}_synth.ys
plugin -i ghdl
ghdl --std=08 rtl/{e}.vhd synth/{e}_timed.vhd -e {e}_timed
synth_ice40 -top {e}_timed -json build/{e}.json
# then:
#   nextpnr-ice40 --up5k --package sg48 --json build/{e}.json \\
#       --report build/{e}_nextpnr.json --pcf-allow-unconstrained --freq 40 --seed 1
"""

    def _readme(self, design: GeneratedDesign) -> str:
        e = design.entity
        return f"""# Synthesis flow — {e}

When the OSS CAD Suite is installed, the pipeline runs this flow itself and the
report's QoR is **measured** (source `nextpnr-ice40`, iCE40 UP5K, seed 1):
`{e}_timed.vhd` is a registered timing harness (serial-in / XOR-reduced-out) so
the DUT's combinational depth is timed as a reg-to-reg path regardless of width.

Manual run from the project root:

```bash
yosys -p 'plugin -i ghdl' -s synth/{e}_synth.ys
nextpnr-ice40 --up5k --package sg48 --json build/{e}.json \\
    --report build/{e}_nextpnr.json --pcf-allow-unconstrained --freq 40 --seed 1
```

`build/{e}_nextpnr.json` contains the achieved Fmax; the yosys log contains
SB_LUT4/SB_DFF counts. For hardware deployment continue with `icepack` and a
pin-constraint (.pcf) file for your board.

Vendor flows: read `../rtl/{e}.vhd` into Vivado/Quartus and feed the reported
LUT/FF/Fmax back as the design's QoR; the loop consumes real numbers directly.
"""

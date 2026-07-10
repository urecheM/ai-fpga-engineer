"""Simulation runner: GHDL executes the emitted RTL against the oracle testbench.

If ``ghdl`` is on PATH the flow runs here and now — analyze (VHDL-2008),
elaborate, run, parse — and ``SimulationResult.passed`` reflects the *actual
RTL's* behaviour. If GHDL is absent, a ready-to-run script is emitted and
``ran=False`` says so honestly; with ``AIFPGA_REQUIRE_TOOLS=1`` (CI) the
absent-tool path is a hard failure so a green badge means the simulator ran.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass

from ..agents.base import Agent
from ..core import toolchain
from ..core.spec import Specification
from ..hdl.library import GeneratedDesign
from ..agents.verification_agent import VerificationResult


@dataclass
class SimulationResult:
    ran: bool
    passed: bool | None            # None when the simulator did not run
    backend: str                   # "ghdl" | "flow-emitted"
    log: str = ""


class SimulationAgent(Agent):
    name = "simulation"

    def run(self, project, spec: Specification, design: GeneratedDesign,
            vres: VerificationResult) -> SimulationResult:
        e, tb = design.entity, vres.tb_entity
        self._emit_flow(project, e, tb)

        if not toolchain.detect().sim_ok:
            if toolchain.require_tools():
                raise RuntimeError("AIFPGA_REQUIRE_TOOLS=1 but ghdl is not installed")
            self.log(project, "ghdl not installed: the RTL was NOT executed. "
                              "Runnable flow emitted at tb/run_ghdl.sh "
                              "(install the OSS CAD Suite)", "warn")
            return SimulationResult(False, None, "flow-emitted")

        log = ""
        steps = [
            ["ghdl", "-a", "--std=08", f"../rtl/{e}.vhd", f"{tb}.vhd"],
            ["ghdl", "-e", "--std=08", tb],
            ["ghdl", "-r", "--std=08", tb],
        ]
        rc = 0
        for cmd in steps:
            try:
                out = subprocess.run(cmd, cwd=str(project.root / "tb"),
                                     capture_output=True, text=True, timeout=600)
            except Exception as exc:
                self.log(project, f"ghdl invocation failed: {exc}", "error")
                return SimulationResult(True, False, "ghdl", f"{log}\n{exc}")
            log += out.stdout + out.stderr
            rc = out.returncode
            if rc != 0:
                break
        project.write(f"reports/{e}_ghdl.log", log, "ghdl_log")

        passed = rc == 0 and "ALL TESTS PASSED" in log
        if passed:
            self.log(project, f"GHDL executed tb/{tb}.vhd: PASSED "
                              f"({vres.tb_vectors} vectors)", "success")
        else:
            self.log(project, "GHDL simulation FAILED (see reports/"
                              f"{e}_ghdl.log)", "error")
        return SimulationResult(True, passed, "ghdl", log)

    # ------------------------------------------------------------------
    def _emit_flow(self, project, e: str, tb: str) -> None:
        project.write("tb/run_ghdl.sh", f"""#!/bin/sh
# Cycle-accurate simulation of {e} against the oracle testbench.
set -e
ghdl -a --std=08 ../rtl/{e}.vhd {tb}.vhd
ghdl -e --std=08 {tb}
ghdl -r --std=08 {tb}
""", "ghdl_script")
        project.write("tb/Makefile", f"""sim:
\tsh run_ghdl.sh

clean:
\trm -f work-obj08.cf {tb}
""", "ghdl_makefile")

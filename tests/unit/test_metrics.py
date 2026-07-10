from __future__ import annotations

from hdleval.metrics.static_analysis import analyze_vhdl
from hdleval.metrics.resources import resource_metrics
from hdleval.toolchain.detect import ToolResult


FSM = """
entity t is port(clk: in bit); end entity;
architecture a of t is type state_t is (S0,S1,S2); signal state: state_t;
begin process(clk) begin if rising_edge(clk) then
case state is when S0=> state<=S1; when S1=>state<=S2; when others=>state<=S0;
end case; end if; end process; end architecture;
"""


def test_static_counts_states():
    m = analyze_vhdl(FSM)
    assert m.fsm_states == 3
    assert m.processes >= 1
    assert m.lines > 3


def test_resource_metrics_skipped():
    r = resource_metrics(ToolResult(status="skipped"))
    assert not r.available


def test_resource_metrics_ok():
    tr = ToolResult(status="ok", metrics={"luts": 20, "ffs": 8})
    r = resource_metrics(tr)
    assert r.available and r.luts == 20 and r.est_fmax_mhz > 0

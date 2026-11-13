from __future__ import annotations

from hdleval.benchmarks.loader import load_suite, reference_hdl
from hdleval.parsing.ports import compare_interfaces, entity_declaration, parse_ports

FIFO = """
library ieee; use ieee.std_logic_1164.all;
entity fifo16 is
  port(clk, rst, wr_en, rd_en : in std_logic;  -- control
       din : in std_logic_vector(7 downto 0);
       dout : out std_logic_vector(7 downto 0);
       full, empty : out std_logic);
end entity;
"""


def test_parse_ports_names_directions_widths():
    ports = {p.name: p for p in parse_ports(FIFO, "fifo16")}
    assert set(ports) == {"clk", "rst", "wr_en", "rd_en", "din", "dout", "full", "empty"}
    assert ports["din"].direction == "in" and ports["din"].width == 8
    assert ports["full"].width == 1 and not ports["full"].is_vector


def test_compare_detects_width_direction_and_name():
    ref = parse_ports(FIFO, "fifo16")
    bad = FIFO.replace("dout : out std_logic_vector(7", "dout : out std_logic_vector(15")
    bad = bad.replace("full, empty", "is_full, empty")
    problems = compare_interfaces(ref, parse_ports(bad, "fifo16"))
    assert "dout: width 16, expected 8" in problems
    assert "missing port full" in problems and "unexpected port is_full" in problems
    assert compare_interfaces(ref, parse_ports(FIFO, "fifo16")) == []


def test_every_reference_parses_and_has_a_declaration():
    for b in load_suite("v1"):
        ref = reference_hdl(b)
        assert parse_ports(ref, b.entity), b.id
        assert entity_declaration(ref, b.entity).lower().startswith("entity"), b.id

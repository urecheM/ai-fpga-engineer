from __future__ import annotations

from hdleval.parsing.hdl_extract import extract_vhdl


def test_extract_fenced():
    raw = "Here you go:\n```vhdl\nentity foo is end entity;\n```\ndone"
    e = extract_vhdl(raw)
    assert e.found and e.entity == "foo"


def test_extract_none():
    e = extract_vhdl("no code at all")
    assert not e.found and e.entity is None


def test_extract_prefers_entity_block():
    raw = "```\njust text\n```\n```vhdl\nentity bar is end entity;\n```"
    e = extract_vhdl(raw)
    assert e.entity == "bar"

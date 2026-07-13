from __future__ import annotations

from hdleval.cli import build_parser, main


def test_list_benchmarks(capsys=None):
    rc = main(["list-benchmarks"])
    assert rc == 0


def test_toolchain():
    assert main(["toolchain"]) == 0


def test_run_and_report(tmp_path):
    # tiny run over arithmetic only, then regenerate report from the DB
    import yaml

    exp = {
        "name": "cli-smoke",
        "models": ["reference-golden"],
        "prompts": ["direct"],
        "benchmarks": {"suite_version": "v1", "categories": ["arithmetic"]},
        "trials": 1,
    }
    p = tmp_path / "exp.yaml"
    p.write_text(yaml.safe_dump(exp))
    out = tmp_path / "out"
    db = tmp_path / "db.sqlite"
    assert main(["run", str(p), "--out", str(out), "--db", str(db)]) == 0
    assert main(["report", "cli-smoke", "--out", str(out), "--db", str(db)]) == 0


def test_parser_builds():
    assert build_parser() is not None

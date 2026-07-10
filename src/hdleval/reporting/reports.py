"""Generate JSON, CSV, Markdown and HTML artifacts from records + leaderboard.

All outputs are derived; nothing here is hand-authored. ``write_all_reports``
is called by ``reproduce.py`` so every table in the paper is regenerated.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from ..leaderboard.aggregate import Leaderboard


def _md_table(rows: list[dict[str, Any]], cols: list[str]) -> str:
    if not rows:
        return "_no data_\n"
    head = "| " + " | ".join(cols) + " |\n"
    sep = "| " + " | ".join("---" for _ in cols) + " |\n"
    body = ""
    for r in rows:
        body += "| " + " | ".join(str(r.get(c, "")) for c in cols) + " |\n"
    return head + sep + body


def write_all_reports(
    records: list[dict[str, Any]],
    leaderboard: Leaderboard,
    out_dir: str | Path,
    experiment_name: str = "experiment",
) -> dict[str, str]:
    out = Path(out_dir)
    (out / "reports").mkdir(parents=True, exist_ok=True)
    (out / "leaderboards").mkdir(parents=True, exist_ok=True)
    (out / "tables").mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}

    # raw JSON
    p = out / "reports" / f"{experiment_name}_records.json"
    p.write_text(json.dumps(records, indent=2, sort_keys=True))
    written["records_json"] = str(p)

    # leaderboard JSON
    p = out / "leaderboards" / f"{experiment_name}_leaderboard.json"
    p.write_text(json.dumps(leaderboard.to_dict(), indent=2, sort_keys=True))
    written["leaderboard_json"] = str(p)

    # CSV export (per-benchmark rows)
    p = out / "tables" / f"{experiment_name}_results.csv"
    with p.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["benchmark", "model", "prompt", "trial", "passed", "failure_class",
                    "duration_s", "latency_s", "tokens"])
        for r in records:
            m = r.get("metrics", {})
            w.writerow([r["benchmark"], r["model"], r["prompt"], r["trial"],
                        int(r["passed"]), r.get("failure_class", ""),
                        r.get("duration_s", ""), m.get("inference_latency_s", ""),
                        int(m.get("prompt_tokens", 0)) + int(m.get("completion_tokens", 0))])
    written["results_csv"] = str(p)

    # Markdown report
    cols = ["model", "prompt", "n", "pass_rate", "pass_ci95", "compile_rate",
            "synth_rate", "avg_latency_s", "avg_tokens", "avg_retries"]
    md = [f"# Results: {experiment_name}\n",
          "_This report is generated automatically from the experiment registry._\n",
          "\n## Overall leaderboard\n\n", _md_table(leaderboard.overall, cols)]
    for cat, rows in leaderboard.by_category.items():
        md.append(f"\n## Category: {cat}\n\n")
        md.append(_md_table(rows, cols))
    for tier, rows in leaderboard.by_difficulty.items():
        md.append(f"\n## Difficulty tier: {tier}\n\n")
        md.append(_md_table(rows, cols))
    p = out / "reports" / f"{experiment_name}_report.md"
    p.write_text("".join(md))
    written["report_md"] = str(p)

    # HTML dashboard
    p = out / "reports" / f"{experiment_name}_dashboard.html"
    p.write_text(_html_dashboard(experiment_name, leaderboard, records))
    written["dashboard_html"] = str(p)

    return written


def _html_dashboard(name: str, lb: Leaderboard, records: list[dict[str, Any]]) -> str:
    def table(rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "<p>no data</p>"
        cols = ["model", "prompt", "n", "pass_rate", "compile_rate", "synth_rate",
                "avg_latency_s", "avg_tokens"]
        h = "<tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"
        b = "".join("<tr>" + "".join(f"<td>{r.get(c,'')}</td>" for c in cols) + "</tr>"
                    for r in rows)
        return f"<table>{h}{b}</table>"

    cat_sections = "".join(
        f"<h3>{c}</h3>{table(rows)}" for c, rows in lb.by_category.items()
    )
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{name} dashboard</title>
<style>body{{font-family:system-ui,Arial;margin:2rem;color:#1a1a2e}}
table{{border-collapse:collapse;margin:1rem 0}}
th,td{{border:1px solid #ccc;padding:.4rem .6rem;text-align:left}}
th{{background:#16213e;color:#fff}}h1{{color:#16213e}}</style></head>
<body><h1>{name}</h1>
<p>Auto-generated dashboard · {len(records)} benchmark executions.</p>
<h2>Overall leaderboard</h2>{table(lb.overall)}
<h2>By category</h2>{cat_sections}
</body></html>"""

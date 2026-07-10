"""Dependency-free SVG figure generation.

Publication figures are emitted as standalone SVG so they render everywhere and
regenerate deterministically without matplotlib. A matplotlib backend can be
substituted behind the same functions if raster output is required.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

_PALETTE = ["#16213e", "#0f3460", "#533483", "#e94560", "#2a9d8f", "#e9c46a"]


def _bar_chart(title: str, labels: list[str], values: list[float],
               ymax: float = 1.0, ylabel: str = "") -> str:
    w, h = 640, 380
    pad_l, pad_b, pad_t = 60, 90, 50
    plot_w = w - pad_l - 20
    plot_h = h - pad_b - pad_t
    n = max(1, len(values))
    bw = plot_w / n * 0.65
    gap = plot_w / n
    bars = []
    for i, (lab, v) in enumerate(zip(labels, values)):
        bh = (v / ymax) * plot_h if ymax else 0
        x = pad_l + i * gap + (gap - bw) / 2
        y = pad_t + plot_h - bh
        c = _PALETTE[i % len(_PALETTE)]
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{c}"/>')
        bars.append(f'<text x="{x+bw/2:.1f}" y="{y-6:.1f}" font-size="11" text-anchor="middle">{v:.2f}</text>')
        bars.append(f'<text x="{x+bw/2:.1f}" y="{pad_t+plot_h+16:.1f}" font-size="10" '
                    f'text-anchor="middle" transform="rotate(20 {x+bw/2:.1f} {pad_t+plot_h+16:.1f})">{lab}</text>')
    axis = (f'<line x1="{pad_l}" y1="{pad_t+plot_h}" x2="{pad_l+plot_w}" y2="{pad_t+plot_h}" stroke="#333"/>'
            f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t+plot_h}" stroke="#333"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="system-ui,Arial">'
            f'<rect width="{w}" height="{h}" fill="white"/>'
            f'<text x="{w/2}" y="26" font-size="16" font-weight="bold" text-anchor="middle">{title}</text>'
            f'<text x="16" y="{pad_t+plot_h/2}" font-size="11" text-anchor="middle" '
            f'transform="rotate(-90 16 {pad_t+plot_h/2})">{ylabel}</text>'
            f'{axis}{"".join(bars)}</svg>')


def write_all_figures(leaderboard: dict[str, Any], records: list[dict[str, Any]],
                      out_dir: str | Path) -> dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}

    # 1. overall pass rate by model
    ov = leaderboard.get("overall", [])
    if ov:
        labels = [f'{r["model"]}/{r["prompt"]}' for r in ov]
        svg = _bar_chart("Overall pass rate by model", labels,
                         [r["pass_rate"] for r in ov], ylabel="pass rate")
        p = out / "pass_rate_by_model.svg"
        p.write_text(svg)
        written["pass_rate_by_model"] = str(p)

    # 2. pass rate by category (first model)
    cats = leaderboard.get("by_category", {})
    if cats:
        labels = list(cats.keys())
        vals = [rows[0]["pass_rate"] if rows else 0.0 for rows in cats.values()]
        svg = _bar_chart("Pass rate by category", labels, vals, ylabel="pass rate")
        p = out / "pass_rate_by_category.svg"
        p.write_text(svg)
        written["pass_rate_by_category"] = str(p)

    # 3. failure distribution
    fail_counts: dict[str, int] = {}
    for r in records:
        fail_counts[r.get("failure_class", "none")] = fail_counts.get(r.get("failure_class", "none"), 0) + 1
    if fail_counts:
        labels = list(fail_counts.keys())
        vals = [float(v) for v in fail_counts.values()]
        svg = _bar_chart("Failure-class distribution", labels, vals,
                         ymax=max(vals) or 1, ylabel="count")
        p = out / "failure_distribution.svg"
        p.write_text(svg)
        written["failure_distribution"] = str(p)

    # 4. difficulty tier pass rates
    tiers = leaderboard.get("by_difficulty", {})
    if tiers:
        labels = list(tiers.keys())
        vals = [rows[0]["pass_rate"] if rows else 0.0 for rows in tiers.values()]
        svg = _bar_chart("Pass rate by difficulty tier", labels, vals, ylabel="pass rate")
        p = out / "pass_rate_by_difficulty.svg"
        p.write_text(svg)
        written["pass_rate_by_difficulty"] = str(p)

    return written

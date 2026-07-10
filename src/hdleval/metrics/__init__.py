"""Quantitative metrics: static HDL analysis + resource/timing accounting."""
from __future__ import annotations

from .static_analysis import StaticMetrics, analyze_vhdl
from .resources import ResourceMetrics, resource_metrics

__all__ = ["StaticMetrics", "analyze_vhdl", "ResourceMetrics", "resource_metrics"]

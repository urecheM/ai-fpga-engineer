"""Quantitative metrics: static HDL analysis + resource/timing accounting."""

from __future__ import annotations

from .resources import ResourceMetrics, resource_metrics
from .static_analysis import StaticMetrics, analyze_vhdl

__all__ = ["ResourceMetrics", "StaticMetrics", "analyze_vhdl", "resource_metrics"]

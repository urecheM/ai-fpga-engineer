"""Derive resource-efficiency metrics from synthesis output."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from ..toolchain.detect import ToolResult


@dataclass(frozen=True)
class ResourceMetrics:
    luts: float
    ffs: float
    dsp: float
    bram: float
    est_fmax_mhz: float
    area_efficiency: float  # useful-cells / total-cells proxy
    available: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def resource_metrics(synth: ToolResult, *, clock_ns: float = 10.0) -> ResourceMetrics:
    if not synth.ok:
        return ResourceMetrics(0, 0, 0, 0, 0.0, 0.0, available=False)
    m = synth.metrics
    luts = m.get("luts", 0.0)
    ffs = m.get("ffs", 0.0)
    dsp = m.get("dsp", 0.0)
    bram = m.get("bram", 0.0)
    total = luts + ffs + dsp * 8 + bram * 16
    # A conservative Fmax proxy: fewer combinational levels -> higher Fmax.
    est_fmax = round(1000.0 / max(clock_ns, 0.5) * (1.0 / (1.0 + luts / 256.0)), 1)
    area_eff = round((ffs + 1) / (total + 1), 3)
    return ResourceMetrics(luts, ffs, dsp, bram, est_fmax, area_eff, available=True)

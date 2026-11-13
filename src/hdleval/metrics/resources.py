from __future__ import annotations

from dataclasses import asdict, dataclass

from ..toolchain.detect import ToolResult


@dataclass(frozen=True)
class ResourceMetrics:
    luts: float
    ffs: float
    dsp: float
    bram: float
    fmax_mhz: float | None
    fmax_source: str
    area_efficiency: float
    available: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def resource_metrics(synth: ToolResult, pnr: ToolResult | None = None) -> ResourceMetrics:
    if not synth.ok:
        return ResourceMetrics(0, 0, 0, 0, None, "not_measured", 0.0, available=False)
    m = synth.metrics
    luts = m.get("luts", 0.0)
    ffs = m.get("ffs", 0.0)
    dsp = m.get("dsp", 0.0)
    bram = m.get("bram", 0.0)
    total = luts + ffs + dsp * 8 + bram * 16

    area_eff = round((ffs + 1) / (total + 1), 3)
    if pnr is not None and pnr.ok and "fmax_mhz" in pnr.metrics:
        fmax: float | None = pnr.metrics["fmax_mhz"]
        source = "nextpnr-ice40-up5k"
    else:
        fmax, source = None, "not_measured"
    return ResourceMetrics(luts, ffs, dsp, bram, fmax, source, area_eff, available=True)

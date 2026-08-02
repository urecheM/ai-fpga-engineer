"""Model pricing table and cost computation.

Prices are USD per 1M tokens, versioned by effective date so historical runs
can be re-priced correctly even after a provider changes its rates. Unknown
model ids (e.g. the synthetic provider's ``synthetic-f{fidelity}``) price at
$0.0 rather than raising, so non-billed runs still flow through unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PriceEntry:
    effective_date: str  # ISO date, YYYY-MM-DD
    input_per_1m: float
    output_per_1m: float


# Newest entry last; lookup picks the last entry whose effective_date <= today.
_PRICE_TABLE: dict[str, list[PriceEntry]] = {
    "claude-fable-5": [PriceEntry("2026-01-01", 10.00, 50.00)],
    "claude-mythos-5": [PriceEntry("2026-01-01", 10.00, 50.00)],
    "claude-opus-4-8": [PriceEntry("2026-01-01", 5.00, 25.00)],
    "claude-opus-4-7": [PriceEntry("2026-01-01", 5.00, 25.00)],
    "claude-opus-4-6": [PriceEntry("2026-01-01", 5.00, 25.00)],
    "claude-sonnet-5": [PriceEntry("2026-01-01", 3.00, 15.00)],
    "claude-sonnet-4-6": [PriceEntry("2026-01-01", 3.00, 15.00)],
    "claude-haiku-4-5": [PriceEntry("2026-01-01", 1.00, 5.00)],
}


def price_for(model_id: str, as_of: str | None = None) -> PriceEntry | None:
    """Return the price entry effective for ``model_id`` as of a given date.

    ``as_of`` defaults to "now" (i.e. the latest entry). Returns ``None`` for
    unknown model ids.
    """
    entries = _PRICE_TABLE.get(model_id)
    if not entries:
        return None
    if as_of is None:
        return entries[-1]
    applicable = [e for e in entries if e.effective_date <= as_of]
    return applicable[-1] if applicable else None


def compute_cost_usd(
    model_id: str, input_tokens: int, output_tokens: int, as_of: str | None = None
) -> float:
    """Compute the USD cost of a call. Returns 0.0 for unpriced model ids."""
    entry = price_for(model_id, as_of)
    if entry is None:
        return 0.0
    return (input_tokens / 1_000_000) * entry.input_per_1m + (
        output_tokens / 1_000_000
    ) * entry.output_per_1m

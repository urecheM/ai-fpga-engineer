from __future__ import annotations

from hdleval.registry.pricing import compute_cost_usd, price_for


def test_unknown_model_id_prices_zero():
    assert compute_cost_usd("synthetic-f0.8", 1000, 1000) == 0.0
    assert price_for("synthetic-f0.8") is None


def test_known_model_id_computes_cost():
    cost = compute_cost_usd("claude-sonnet-5", 1_000_000, 1_000_000)
    assert cost == 18.00


def test_price_for_returns_latest_entry():
    entry = price_for("claude-haiku-4-5")
    assert entry is not None
    assert entry.input_per_1m == 1.00
    assert entry.output_per_1m == 5.00

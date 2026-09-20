from __future__ import annotations

from hdleval.models.base import ModelResponse, estimate_cost
from hdleval.registry.pricing import compute_cost_usd, price_for


def test_estimate_cost_matches_compute_cost_usd():
    resp = ModelResponse(
        text="",
        provider="anthropic",
        model_id="claude-sonnet-5",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )
    assert estimate_cost(resp) == compute_cost_usd("claude-sonnet-5", 1_000_000, 1_000_000)


def test_estimate_cost_zero_for_synthetic_model():
    resp = ModelResponse(
        text="",
        provider="synthetic",
        model_id="synthetic-f0.8",
        prompt_tokens=1000,
        completion_tokens=1000,
    )
    assert estimate_cost(resp) == 0.0


def test_model_response_cost_usd_defaults_to_zero():
    resp = ModelResponse(text="", provider="reference", model_id="reference-golden")
    assert resp.cost_usd == 0.0


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

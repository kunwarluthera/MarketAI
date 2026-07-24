from datetime import UTC, datetime
from app.evidence.engine import evaluate


def test_price_ema_evidence_is_deterministic():
    t = datetime(2026, 1, 1, tzinfo=UTC)
    expected = evaluate("PRICE_ABOVE_EMA", {"close": 105, "ema": 100, "atr": 10}, t)
    assert expected == evaluate("PRICE_ABOVE_EMA", {"close": 105, "ema": 100, "atr": 10}, t)
    assert expected["direction"] == "bullish"
    assert expected["strength"] == 0.5


def test_missing_and_expiry_are_explicit():
    t = datetime(2026, 1, 1, tzinfo=UTC)
    assert evaluate("RSI_STATE", {}, t)["direction"] == "unavailable"
    assert evaluate("PROVIDER_FRESHNESS", {"status": "stale"}, t)["direction"] == "unavailable"

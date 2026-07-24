from app.robustness.core import classify_historical_regime, robustness_summary


def test_regime_definition_is_deterministic_and_historical():
    result = classify_historical_regime({"volatility": 0.04, "relative_volume": 1})
    assert result["regime"] == "high_volatility"
    assert result["historical_only"] is True


def test_robustness_summary_preserves_regime_weaknesses():
    result = robustness_summary(
        [
            {"status": "completed", "regime": "normal", "accuracy": 0.8},
            {"status": "completed", "regime": "high", "accuracy": 0.4},
        ]
    )
    assert result["regimes"]["high"]["mean"] == 0.4
    assert result["regimes"]["normal"]["fold_count"] == 1

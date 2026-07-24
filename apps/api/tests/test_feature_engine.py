from app.features.engine import (
    atr,
    bar_vwap,
    ema,
    period_return,
    relative_volume,
    rsi,
    sma,
    trend_slope,
)


def candles():
    return [
        {"open": i, "high": i + 2, "low": i - 1, "close": i, "volume": 100 + i}
        for i in range(1, 30)
    ]


def test_deterministic_moving_averages_and_returns():
    data = candles()
    assert sma(data, 3) == 28
    assert ema(data, 3) == 28
    assert period_return(data, 1) == (29 / 28) - 1
    assert sma(data, 3) == sma(data, 3)


def test_deterministic_momentum_volatility_volume_and_slope():
    data = candles()
    assert rsi(data, 14) == 100
    assert atr(data, 3) == 3
    assert bar_vwap(data) is not None
    assert relative_volume(data, 5) is not None
    assert trend_slope(data, 5) == 1

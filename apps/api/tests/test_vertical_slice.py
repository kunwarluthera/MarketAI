from datetime import timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from app.domain import Candle, Tick, aggregate_candle, features, now, regime
from app.main import app
from app.portfolio.domain import realised_pnl, weighted_average


def test_candle_aggregation_and_validation() -> None:
    timestamp = now()
    candle = aggregate_candle(
        [
            Tick("TCS", Decimal("100"), 2, timestamp),
            Tick("TCS", Decimal("102"), 3, timestamp + timedelta(seconds=1)),
        ]
    )
    assert (candle.open, candle.high, candle.volume) == (Decimal("100"), Decimal("102"), 5)


def test_features_and_regime() -> None:
    timestamp = now()
    candles = [
        Candle(
            "X",
            Decimal(100 + i),
            Decimal(102 + i),
            Decimal(99 + i),
            Decimal(101 + i),
            1000 + i * 200,
            timestamp + timedelta(minutes=i),
            timestamp + timedelta(minutes=i, seconds=59),
        )
        for i in range(5)
    ]
    assert features(candles)["ready"] is True
    assert regime(candles)["regime"] == "trending_up"


def test_weighted_average_and_realised_pnl() -> None:
    assert weighted_average(Decimal(10), Decimal(100), Decimal(10), Decimal(110)) == Decimal(
        "105.0000"
    )
    assert realised_pnl(Decimal(10), Decimal(100), Decimal(110), Decimal(1), Decimal(1)) == Decimal(
        "98.00"
    )


def test_postgresql_backed_critical_flow() -> None:
    from app.common.db import SessionLocal
    from app.paper_trading.service import seed

    with SessionLocal.begin() as session:
        seed(session)
    client = TestClient(app)
    login = client.post("/api/v1/auth/login", json={"username": "demo", "password": "papertrade"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    held = {p["symbol"] for p in client.get("/api/v1/paper/positions", headers=headers).json()}
    symbol = next(
        row["symbol"]
        for row in client.get("/api/v1/scanner/results", headers=headers).json()
        if row["symbol"] not in held and row["decision"] == "BUY"
    )
    decision = client.post(
        "/api/v1/decisions/generate", headers=headers, json={"instrument_id": symbol}
    ).json()
    approval = decision["approval_id"]
    first = client.post(
        f"/api/v1/approvals/{approval}/approve",
        headers={**headers, "Idempotency-Key": f"test-{approval}"},
    )
    second = client.post(
        f"/api/v1/approvals/{approval}/approve",
        headers={**headers, "Idempotency-Key": f"test-{approval}"},
    )
    assert first.status_code == 200 and second.json()["id"] == first.json()["id"]
    position = next(
        p
        for p in client.get("/api/v1/paper/positions", headers=headers).json()
        if p["symbol"] == symbol
    )
    exited = client.post(
        f"/api/v1/paper/positions/{position['id']}/exit", headers=headers, json={"reason": "manual"}
    )
    assert exited.status_code == 200
    assert client.post("/api/v1/paper/reconcile", headers=headers).json()["status"] == "ok"
    assert client.get("/api/v1/audit", headers=headers).json()

from fastapi.testclient import TestClient

from app.main import app


def test_statistical_validation_reads_require_authentication():
    client = TestClient(app)
    response = client.get("/api/v3/ml/runtime/statistical-validation")
    assert response.status_code == 401


def test_statistical_validation_artifacts_require_authentication():
    client = TestClient(app)
    for path in (
        "/api/v3/ml/runtime/statistical-validation/request-x",
        "/api/v3/ml/runtime/statistical-validation/request-x/manifest",
        "/api/v3/ml/runtime/statistical-validation/request-x/events",
        "/api/v3/ml/runtime/statistical-validation/request-x/lifecycle",
        "/api/v3/ml/runtime/statistical-validation/request-x/replays",
        "/api/v3/ml/runtime/statistical-validation/request-x/replay/replay-x",
    ):
        response = client.get(path)
        assert response.status_code == 401


def test_statistical_lifecycle_mutations_require_authentication():
    client = TestClient(app)
    response = client.post(
        "/api/v3/admin/ml/runtime/statistical-validation/request-x/invalidate",
        json={"reason": "test"},
    )
    assert response.status_code == 401


def test_statistical_replay_mutation_requires_authentication():
    client = TestClient(app)
    response = client.post(
        "/api/v3/admin/ml/runtime/statistical-validation/request-x/replay",
        json={"payload": {}},
    )
    assert response.status_code == 401


def test_lifecycle_action_is_restricted_to_governed_actions():
    client = TestClient(app)
    login = client.post("/api/v1/auth/login", json={"username": "demo", "password": "papertrade"})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.post(
        "/api/v3/admin/ml/runtime/statistical-validation/request-x/not-supported",
        headers=headers,
        json={"reason": "test"},
    )
    assert response.status_code in {400, 422, 500}


def test_caller_supplied_statistics_are_rejected():
    client = TestClient(app)
    login = client.post("/api/v1/auth/login", json={"username": "demo", "password": "papertrade"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.post(
        "/api/v3/admin/ml/runtime/statistical-validation/request",
        headers=headers,
        json={
            "parent_validation_request_identity": "p",
            "prediction_result_identity": "x",
            "threshold": 0.99,
            "probabilities": [1.0],
        },
    )
    assert response.status_code == 422

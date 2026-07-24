from app.attribution.core import checksum


def test_runtime_checksum_is_deterministic():
    state = {"queue_depth": 2, "latency_ms": [10, 20]}
    assert checksum(state) == checksum({"latency_ms": [10, 20], "queue_depth": 2})


def test_runtime_slo_breach_is_deterministic():
    target, observed = 0.99, 0.97
    result = {
        "target": target,
        "observed": observed,
        "compliant": observed >= target,
        "reason": "availability_breach",
    }
    assert result["compliant"] is False
    assert checksum(result) == checksum(result)

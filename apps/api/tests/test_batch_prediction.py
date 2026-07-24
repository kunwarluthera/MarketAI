import pytest

from app.batch_prediction.core import checksum, ordered_members, retry_decision, transition


def test_universe_order_is_deterministic():
    members = ordered_members({"members": [{"symbol": "b"}, {"symbol": "A"}]})
    assert [item["symbol"] for item in members] == ["A", "b"]
    assert checksum(members) == checksum(members)


def test_invalid_transition_is_rejected():
    transition("created", "eligible")
    with pytest.raises(ValueError, match="invalid_batch_transition"):
        transition("created", "running")


def test_retry_is_bounded_and_exponential():
    assert (
        retry_decision(1, 3, "temporary_resource_unavailable", {"temporary_resource_unavailable"})[
            "next_delay_seconds"
        ]
        == 1
    )
    assert (
        retry_decision(3, 3, "temporary_resource_unavailable", {"temporary_resource_unavailable"})[
            "terminal"
        ]
        is True
    )
    assert (
        retry_decision(1, 3, "invalid_input", {"temporary_resource_unavailable"})["terminal"]
        is True
    )

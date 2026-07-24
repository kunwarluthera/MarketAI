from datetime import datetime, timezone

from app.opportunity.engine import OpportunityInput, evaluate_opportunity


def test_alignment_is_deterministic_and_neutral() -> None:
    args = OpportunityInput(
        "instrument-1", datetime(2026, 1, 1, tzinfo=timezone.utc), ("positive",), ("positive",)
    )
    first = evaluate_opportunity(args)
    assert first == evaluate_opportunity(args)
    assert first.orientation == "positive_alignment"
    assert first.state == "medium_priority_research"
    assert first.score == 33


def test_missing_input_blocks_priority() -> None:
    result = evaluate_opportunity(
        OpportunityInput(
            "instrument-1",
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            ("positive",),
            required_inputs_missing=("MISSING_EVIDENCE",),
        )
    )
    assert result.state == "insufficient_data"
    assert result.score == 10
    assert "MISSING_EVIDENCE" in result.blocking_reasons


def test_expired_opportunity_is_not_active() -> None:
    result = evaluate_opportunity(
        OpportunityInput(
            "instrument-1",
            datetime(2026, 1, 2, tzinfo=timezone.utc),
            expires_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    )
    assert result.state == "expired"
    assert result.orientation == "unavailable"
    assert result.score == 0

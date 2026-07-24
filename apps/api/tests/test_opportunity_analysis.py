from datetime import datetime, timezone, timedelta

from app.opportunity.analysis import analyze, assemble_as_of


def test_assembler_excludes_future_inputs() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = assemble_as_of(
        "i",
        now,
        [
            {"id": "past", "evaluated_at": now - timedelta(minutes=1)},
            {"id": "future", "evaluated_at": now + timedelta(minutes=1)},
        ],
        [],
    )
    assert [x["id"] for x in result.technical_items] == ["past"]


def test_analysis_exposes_support_and_conflict() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = analyze(
        assemble_as_of("i", now, [{"direction": "positive"}], [{"impact": "negative"}])
    )
    assert result.readiness == "degraded"
    assert result.conflicts[0]["conflict_code"] == "TECHNICAL_EXTERNAL_CONFLICT"

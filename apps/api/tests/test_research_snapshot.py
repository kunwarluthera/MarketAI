from datetime import datetime, timezone

from app.research.snapshot import ResearchSnapshotInput, build_snapshot, validate_snapshot


def test_snapshot_is_reproducible_and_complete() -> None:
    args = ResearchSnapshotInput(
        "i",
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        {"session": "open"},
        {"ema": 1},
        {"ready": True},
        {"ready": True},
        {"state": "monitor"},
        {"source": "test"},
    )
    snapshot = build_snapshot(args)
    assert validate_snapshot(snapshot) == ()
    assert snapshot["snapshot_identity"] == build_snapshot(args)["snapshot_identity"]


def test_snapshot_validation_reports_missing_sections() -> None:
    assert "MISSING_FEATURES" in validate_snapshot({"schema_version": "2.6.1"})

from app.labels.framework import LabelSpec, OutcomeSpec, calculate_raw_outcome, derive_label


def test_immature_outcome_never_produces_label():
    row = {"evaluated_at": "2026-01-01", "features": {"close": 100}}
    raw = calculate_raw_outcome(row, [], OutcomeSpec("return", "1", 2, 60))
    assert raw["status"] == "immature"
    assert (
        derive_label(raw, LabelSpec("direction", "1", "return", 0.01, -0.01))["status"]
        == "immature"
    )


def test_mature_label_preserves_feature_cutoff():
    row = {"evaluated_at": "2026-01-01", "features": {"close": 100}}
    raw = calculate_raw_outcome(
        row, [{"close": 101, "ended_at": "2026-01-02"}], OutcomeSpec("return", "1", 1, 60)
    )
    label = derive_label(raw, LabelSpec("direction", "1", "return", 0.01, -0.01))
    assert label["label"] == "positive"
    assert raw["feature_cutoff_at"] == "2026-01-01"

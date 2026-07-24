from app.datasets.builder import DatasetSpec, build_dataset, build_feature_row


def snapshot():
    return {
        "schema_version": "2.6.1",
        "snapshot_identity": "s1",
        "instrument_id": "i1",
        "evaluated_at": "2026-01-01T00:00:00+00:00",
        "features": {"ema": 10},
        "opportunity": {"state": "monitor"},
    }


def test_declared_features_are_reproducible_and_missingness_is_explicit():
    spec = DatasetSpec(
        "research_features", "1", ("features.ema", "features.rsi"), ("opportunity.state",)
    )
    first = build_feature_row(snapshot(), spec)
    assert first == build_feature_row(snapshot(), spec)
    assert first["features"]["features.rsi"] is None
    assert "features.rsi" in first["missing_fields"]
    assert "labels" not in first


def test_dataset_identity_and_no_labels():
    result = build_dataset([snapshot()], DatasetSpec("research_features", "1", ("features.ema",)))
    assert result["row_count"] == 1
    assert result["contains_labels"] is False
    assert (
        result["dataset_identity"]
        == build_dataset([snapshot()], DatasetSpec("research_features", "1", ("features.ema",)))[
            "dataset_identity"
        ]
    )

from app.ml.training import (
    TemporalSplitSpec,
    evaluate_binary,
    fit_majority_baseline,
    temporal_split,
    training_manifest,
)


def test_temporal_split_is_ordered_and_disjoint():
    rows = [{"evaluated_at": f"2026-01-0{i}", "row_identity": str(i)} for i in (3, 1, 2, 4, 5)]
    split = temporal_split(rows, TemporalSplitSpec(0.6, 0.2))
    assert [row["row_identity"] for row in split["train"]] == ["1", "2", "3"]
    assert split["validation"][0]["row_identity"] == "4"
    assert split["test"][0]["row_identity"] == "5"


def test_manifest_is_research_only():
    manifest = training_manifest(
        "dataset", "label-v1", {"train": [1], "validation": [], "test": [2]}
    )
    assert manifest["research_only"] is True
    assert manifest["inference_enabled"] is False
    assert manifest["trading_connected"] is False


def test_evaluation_is_deterministic_and_research_only():
    result = evaluate_binary([0, 1, 1, 0], [0.1, 0.8, 0.7, 0.2])
    assert result["accuracy"] == 1.0
    assert result["research_only"] is True


def test_majority_baseline_artifact_is_research_only():
    artifact = fit_majority_baseline([0, 1, 1, 1])
    assert artifact["positive_rate"] == 0.75
    assert artifact["inference_enabled"] is False
    assert artifact["research_only"] is True

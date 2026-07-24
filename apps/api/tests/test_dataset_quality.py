from app.datasets.builder import (
    DatasetSpec,
    build_dataset,
    compare_datasets,
    dataset_quality,
    export_dataset,
)


def test_quality_comparison_and_export_are_deterministic():
    snapshot = {
        "schema_version": "2.6.1",
        "snapshot_identity": "s",
        "instrument_id": "i",
        "evaluated_at": "t",
        "features": {"x": 1},
    }
    dataset = build_dataset([snapshot], DatasetSpec("d", "1", ("features.x", "features.missing")))
    assert dataset_quality(dataset)["quality_status"] == "degraded"
    assert compare_datasets(dataset, dataset)["unchanged"] is True
    assert export_dataset(dataset) == export_dataset(dataset)

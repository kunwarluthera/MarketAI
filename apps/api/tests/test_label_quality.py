from app.labels.framework import compare_labels, label_quality


def test_label_quality_and_comparison_are_deterministic():
    records = [
        {"status": "mature", "label_identity": "a"},
        {"status": "immature", "label_identity": "b"},
    ]
    assert label_quality(records)["mature_count"] == 1
    assert compare_labels(records, records)["unchanged"] is True

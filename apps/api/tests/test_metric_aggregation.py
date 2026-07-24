from app.metric_aggregation.core import aggregate_metric, build_report


def test_aggregation_keeps_weighting_and_dispersion_separate():
    folds = [
        {"fold_number": 1, "status": "completed", "accuracy": 0.5, "test_count": 1},
        {"fold_number": 2, "status": "completed", "accuracy": 1.0, "test_count": 3},
    ]
    result = aggregate_metric(folds, "accuracy")
    assert result["unweighted_mean"] == 0.75
    assert result["support_weighted_mean"] == 0.875
    assert result["best_fold"] == 2
    assert result["worst_fold"] == 1


def test_report_is_reproducible_and_research_only():
    folds = [{"fold_number": 1, "status": "completed", "accuracy": 0.5, "test_count": 1}]
    report = build_report("validation", folds)
    assert report["report_identity"] == build_report("validation", folds)["report_identity"]
    assert report["research_only"] is True

from app.walk_forward.contracts import (
    TrainingRecipe,
    WalkForwardSpec,
    fold_identity,
    generate_folds,
    execute_baseline_folds,
    validation_identity,
)


def test_validation_identity_is_reproducible():
    recipe = TrainingRecipe("baseline", "1", "dataset", "label", "majority_rate_baseline", {})
    spec = WalkForwardSpec("rolling", "1", 10, 2, 2, 2)
    assert validation_identity(recipe, spec) == validation_identity(recipe, spec)


def test_fold_identity_is_independent_by_number():
    assert fold_identity("v", 1) != fold_identity("v", 2)


def test_folds_are_temporal_and_freshly_identified():
    rows = [{"evaluated_at": str(i), "row_identity": str(i)} for i in range(8)]
    folds = generate_folds(rows, WalkForwardSpec("r", "1", 3, 1, 1, 2), "v")
    assert len(folds) == 2
    assert [x["row_identity"] for x in folds[0]["train"]] == ["0", "1", "2"]
    assert folds[0]["fold_identity"] != folds[1]["fold_identity"]


def test_each_fold_trains_independently():
    rows = [{"evaluated_at": str(i), "row_identity": str(i), "label": i % 2} for i in range(10)]
    folds = generate_folds(rows, WalkForwardSpec("r", "1", 4, 1, 1, 2), "v")
    results = execute_baseline_folds(folds)
    assert results
    assert all(result["fresh_model"] for result in results if result["status"] == "completed")

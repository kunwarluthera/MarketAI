from app.model_versioning.core import ModelVersion, compare_versions, version_identity


def test_version_identity_and_semantic_version_are_deterministic():
    version = ModelVersion("research", "baseline", 1, 0, 1, "package")
    assert version.semantic_version == "1.0.1"
    assert version_identity(version) == version_identity(version)


def test_version_comparison_exposes_lineage_differences():
    left = ModelVersion("research", "baseline", 1, 0, 1, "a")
    right = ModelVersion("research", "baseline", 1, 1, 0, "b", version_identity(left))
    result = compare_versions(left, right)
    assert "package_identity" in result["differences"]
    assert result["same_identity"] is False

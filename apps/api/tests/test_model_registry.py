from app.model_registry.contracts import (
    ArtifactMetadata,
    ModelPackageManifest,
    manifest_identity,
    validate_manifest,
)


def test_manifest_validation_requires_research_lineage_and_artifacts():
    manifest = ModelPackageManifest(
        "baseline",
        "1",
        "dataset",
        "training",
        "decision",
        (ArtifactMetadata("weights", "stdlib", "1", "abc", "file://artifact"),),
    )
    assert validate_manifest(manifest) == ()
    assert manifest_identity(manifest) == manifest_identity(manifest)


def test_incomplete_manifest_is_not_accepted():
    manifest = ModelPackageManifest("", "1", "", "", "", ())
    assert "MISSING_MODEL_FAMILY" in validate_manifest(manifest)
    assert "MISSING_ARTIFACTS" in validate_manifest(manifest)

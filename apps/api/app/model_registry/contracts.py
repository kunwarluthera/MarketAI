from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class ArtifactMetadata:
    artifact_type: str
    framework: str
    framework_version: str
    checksum: str
    storage_uri: str


@dataclass(frozen=True)
class ModelPackageManifest:
    model_family: str
    package_version: str
    dataset_identity: str
    training_identity: str
    validation_decision_identity: str
    artifacts: tuple[ArtifactMetadata, ...]


def validate_manifest(manifest: ModelPackageManifest) -> tuple[str, ...]:
    errors = []
    if not manifest.model_family:
        errors.append("MISSING_MODEL_FAMILY")
    if not manifest.dataset_identity:
        errors.append("MISSING_DATASET_LINEAGE")
    if not manifest.training_identity:
        errors.append("MISSING_TRAINING_LINEAGE")
    if not manifest.validation_decision_identity:
        errors.append("MISSING_VALIDATION_LINEAGE")
    if not manifest.artifacts:
        errors.append("MISSING_ARTIFACTS")
    for artifact in manifest.artifacts:
        if not artifact.checksum:
            errors.append("MISSING_ARTIFACT_CHECKSUM")
        if not artifact.storage_uri:
            errors.append("MISSING_STORAGE_REFERENCE")
    return tuple(errors)


def manifest_identity(manifest: ModelPackageManifest) -> str:
    payload = {
        "model_family": manifest.model_family,
        "package_version": manifest.package_version,
        "dataset_identity": manifest.dataset_identity,
        "training_identity": manifest.training_identity,
        "validation_decision_identity": manifest.validation_decision_identity,
        "artifacts": [artifact.__dict__ for artifact in manifest.artifacts],
    }
    return sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

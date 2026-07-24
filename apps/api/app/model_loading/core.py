from dataclasses import dataclass
from hashlib import sha256
import json
import uuid


@dataclass(frozen=True)
class LoadPolicy:
    code: str
    version: str
    allowed_formats: tuple[str, ...] = ("json_manifest",)
    max_bytes: int = 1_000_000


@dataclass(frozen=True)
class ModelHandle:
    handle_id: str
    version_identity: str
    artifact_checksum: str
    format: str


def verify_artifact(
    raw: bytes, declared_checksum: str, artifact_format: str, policy: LoadPolicy
) -> dict:
    if artifact_format not in policy.allowed_formats:
        raise ValueError("Artifact format is not allowlisted")
    if len(raw) > policy.max_bytes:
        raise ValueError("Artifact exceeds policy resource limit")
    checksum = sha256(raw).hexdigest()
    if checksum != declared_checksum:
        raise ValueError("Artifact checksum mismatch")
    return json.loads(raw) if artifact_format == "json_manifest" else {}


def load_handle(
    raw: bytes, checksum: str, artifact_format: str, version_identity: str, policy: LoadPolicy
) -> ModelHandle:
    manifest = verify_artifact(raw, checksum, artifact_format, policy)
    if manifest.get("inference_enabled", False):
        raise ValueError("Inference-enabled artifacts are not loadable in this layer")
    return ModelHandle(str(uuid.uuid4()), version_identity, checksum, artifact_format)

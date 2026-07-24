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


@dataclass(frozen=True)
class CallableInferenceContract:
    """Offline-only callable contract; no dynamic code or network execution."""

    handle: ModelHandle
    operation: str

    def predict(self, rows: list[dict]) -> list[object]:
        if self.operation == "identity":
            return [row.get("value") for row in rows]
        if self.operation.startswith("constant:"):
            value = self.operation.split(":", 1)[1]
            return [float(value) for _ in rows]
        raise ValueError("Unsupported callable inference operation")


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


def load_callable_handle(
    raw: bytes, checksum: str, artifact_format: str, version_identity: str, policy: LoadPolicy
) -> CallableInferenceContract:
    manifest = verify_artifact(raw, checksum, artifact_format, policy)
    if manifest.get("inference_enabled") is not True:
        raise ValueError("Callable inference is not enabled by the approved manifest")
    operation = manifest.get("operation")
    if operation != "identity" and not (
        isinstance(operation, str) and operation.startswith("constant:")
    ):
        raise ValueError("Callable operation is not allowlisted")
    return CallableInferenceContract(
        ModelHandle(str(uuid.uuid4()), version_identity, checksum, artifact_format), operation
    )

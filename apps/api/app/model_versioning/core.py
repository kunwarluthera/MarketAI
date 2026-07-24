from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class ModelVersion:
    namespace: str
    model_code: str
    major: int
    minor: int
    revision: int
    package_identity: str
    predecessor_identity: str | None = None

    @property
    def semantic_version(self) -> str:
        return f"{self.major}.{self.minor}.{self.revision}"


def version_identity(version: ModelVersion) -> str:
    payload = version.__dict__ | {"semantic_version": version.semantic_version}
    return sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def compare_versions(left: ModelVersion, right: ModelVersion) -> dict:
    differences = []
    for field in ("namespace", "model_code", "package_identity", "predecessor_identity"):
        if getattr(left, field) != getattr(right, field):
            differences.append(field)
    if left.semantic_version != right.semantic_version:
        differences.append("semantic_version")
    return {
        "same_identity": version_identity(left) == version_identity(right),
        "differences": differences,
        "research_only": True,
    }

from datetime import UTC, datetime
from hashlib import sha256
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.common.models import ModelLoadManifest
from app.model_loading.core import LoadPolicy, ModelHandle, load_handle


class HandleStore:
    def __init__(self, max_handles: int = 8):
        self.max_handles = max_handles
        self.handles: dict[str, ModelHandle] = {}

    def add(self, handle: ModelHandle) -> None:
        if len(self.handles) >= self.max_handles:
            self.handles.pop(next(iter(self.handles)))
        self.handles[handle.handle_id] = handle

    def unload(self, handle_id: str) -> bool:
        return self.handles.pop(handle_id, None) is not None


def persist_load(
    session: Session,
    raw: bytes,
    checksum: str,
    artifact_format: str,
    version_identity: str,
    policy: LoadPolicy,
    store: HandleStore,
) -> dict:
    handle = load_handle(raw, checksum, artifact_format, version_identity, policy)
    payload = {
        "version_identity": version_identity,
        "handle_id": handle.handle_id,
        "format": artifact_format,
        "checksum": checksum,
        "policy_code": policy.code,
        "status": "loaded",
        "prediction_enabled": False,
    }
    identity = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    if (
        session.scalar(select(ModelLoadManifest).where(ModelLoadManifest.load_identity == identity))
        is None
    ):
        session.add(
            ModelLoadManifest(
                load_identity=identity,
                version_identity=version_identity,
                handle_id=handle.handle_id,
                status="loaded",
                payload=payload,
                created_at=datetime.now(UTC),
            )
        )
    store.add(handle)
    return payload

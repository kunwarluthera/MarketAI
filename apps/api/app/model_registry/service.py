from datetime import UTC, datetime
from hashlib import sha256
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.common.models import ModelRegistryDefinition
from app.model_registry.contracts import ModelPackageManifest, validate_manifest


def persist_definition(
    session: Session, code: str, version: str, definition_type: str, payload: dict
) -> dict:
    identity = sha256(
        json.dumps(
            {"code": code, "version": version, "type": definition_type, "payload": payload},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    if (
        session.scalar(
            select(ModelRegistryDefinition).where(
                ModelRegistryDefinition.definition_identity == identity
            )
        )
        is None
    ):
        session.add(
            ModelRegistryDefinition(
                definition_identity=identity,
                definition_code=code,
                definition_version=version,
                definition_type=definition_type,
                payload=payload,
                enabled=True,
                created_at=datetime.now(UTC),
            )
        )
    return {
        "definition_identity": identity,
        "definition_code": code,
        "definition_version": version,
        "definition_type": definition_type,
    }


def validate_package(manifest: ModelPackageManifest) -> dict:
    return {
        "valid": not validate_manifest(manifest),
        "errors": list(validate_manifest(manifest)),
        "research_only": True,
    }

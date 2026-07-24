from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.common.models import ModelVersionRecord
from app.model_versioning.core import ModelVersion, version_identity


def reserve_version(session: Session, version: ModelVersion) -> dict:
    identity = version_identity(version)
    if (
        session.scalar(
            select(ModelVersionRecord).where(ModelVersionRecord.version_identity == identity)
        )
        is None
    ):
        session.add(
            ModelVersionRecord(
                version_identity=identity,
                namespace=version.namespace,
                model_code=version.model_code,
                semantic_version=version.semantic_version,
                package_identity=version.package_identity,
                predecessor_identity=version.predecessor_identity,
                payload={"research_only": True},
                created_at=datetime.now(UTC),
            )
        )
    return {
        "version_identity": identity,
        "semantic_version": version.semantic_version,
        "research_only": True,
    }

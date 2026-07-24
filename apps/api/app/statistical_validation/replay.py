"""Durable, deterministic replay/comparison workflow for statistical manifests."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.models import StatisticalValidationReplay
from app.prediction_validation.core import checksum
from app.statistical_validation.core import replay_manifest


def persist_replay(
    session: Session,
    *,
    request_identity: str,
    manifest_identity: str,
    manifest: dict,
    current: dict,
) -> dict:
    """Compare a manifest and persist the immutable result idempotently."""
    comparison = replay_manifest(manifest, current)
    identity = checksum(
        {"request": request_identity, "manifest": manifest_identity, "current": current}
    )
    existing = session.scalar(
        select(StatisticalValidationReplay).where(
            StatisticalValidationReplay.replay_identity == identity
        )
    )
    if existing is not None:
        return {
            "replay_identity": identity,
            "status": existing.status,
            "mismatches": existing.mismatches,
            "replay_checksum": existing.replay_checksum,
        }
    payload = {
        "replay_identity": identity,
        "request_identity": request_identity,
        "manifest_identity": manifest_identity,
        "status": comparison["status"],
        "mismatches": comparison["mismatches"],
    }
    replay_checksum = checksum(payload)
    session.add(
        StatisticalValidationReplay(
            replay_identity=identity,
            request_identity=request_identity,
            manifest_identity=manifest_identity,
            status=comparison["status"],
            mismatches=comparison["mismatches"],
            replay_checksum=replay_checksum,
            created_at=datetime.now(UTC),
        )
    )
    return {**payload, "replay_checksum": replay_checksum}

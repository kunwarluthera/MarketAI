from __future__ import annotations
import hashlib
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.common.models import (
    ExternalDuplicateLink,
    ExternalEntityAlias,
    ExternalEntityMapping,
    ExternalClassification,
    ExternalIntelligenceReadiness,
    ExternalItemRelation,
    ExternalItem,
    ExternalRawItem,
    uid,
)
from .engine import (
    ProviderItem,
    canonical_identity,
    canonical_url,
    normalize_text,
)


def capture_raw(session: Session, item: ProviderItem) -> ExternalRawItem:
    checksum = hashlib.sha256(
        json.dumps(item.raw_payload, sort_keys=True, default=str).encode()
    ).hexdigest()
    row = session.scalar(
        select(ExternalRawItem).where(
            ExternalRawItem.provider == item.provider,
            ExternalRawItem.provider_item_id == item.provider_item_id,
            ExternalRawItem.payload_checksum == checksum,
        )
    )
    if row is not None:
        return row
    row = ExternalRawItem(
        id=uid(),
        provider=item.provider,
        provider_item_id=item.provider_item_id,
        retrieved_at=item.retrieved_at,
        payload_checksum=checksum,
        raw_payload=item.raw_payload,
        processing_status="received",
    )
    session.add(row)
    session.flush()
    return row


def relate_items(
    session: Session,
    source_item: ExternalItem,
    target_item: ExternalItem,
    relation_type: str,
    evaluated_at,
    details: dict | None = None,
) -> ExternalItemRelation:
    row = ExternalItemRelation(
        id=uid(),
        source_item_id=source_item.id,
        target_item_id=target_item.id,
        relation_type=relation_type,
        rule_version="1",
        evaluated_at=evaluated_at,
        details=details or {},
    )
    session.add(row)
    session.flush()
    return row


def detect_relationship(left: ExternalItem, right: ExternalItem, evaluated_at):
    from .engine import title_similarity

    score = title_similarity(left.normalized_title, right.normalized_title)
    if left.canonical_url == right.canonical_url:
        return "exact_duplicate", 1.0
    if left.provider == right.provider and score >= 0.9:
        return "near_duplicate", score
    if score >= 0.75 and abs((left.published_at - right.published_at).total_seconds()) <= 86400:
        return "syndicated_copy", score
    return "related_but_distinct", score


def persist_classification(
    session: Session, item: ExternalItem, evaluated_at
) -> ExternalClassification:
    from .engine import assess_importance, classify, confirmation_state, source_tier

    result = classify(item.title, None)
    tier = source_tier("aggregator" if item.provider in {"NEWSAPI", "GNEWS"} else "unknown")
    confirmation = confirmation_state("aggregator", result["confirmation"] == "denied")
    importance = assess_importance(result["category"], "mentioned_only", tier, confirmation)
    row = ExternalClassification(
        id=uid(),
        external_item_id=item.id,
        category_code=result["category"],
        category_version=result["rule_version"],
        impact=result["impact"],
        confirmation=confirmation,
        rule_strength=1,
        matched_phrases=[],
        excluded_phrases=[],
        importance_level=importance["level"],
        importance_signals=importance["signals"],
        evaluated_at=evaluated_at,
    )
    session.add(row)
    session.flush()
    return row


def normalized_identity(item: ProviderItem) -> str:
    return canonical_identity(item)


def process_item(session: Session, item: ProviderItem):
    """Capture, normalize and classify one provider item deterministically."""
    raw = capture_raw(session, item)
    normalized = normalize_and_store(session, item, raw)
    classification = persist_classification(session, normalized, item.retrieved_at)
    return {"raw": raw, "item": normalized, "classification": classification}


def normalize_and_store(session: Session, item: ProviderItem, raw: ExternalRawItem) -> ExternalItem:
    identity = canonical_identity(item)
    row = session.scalar(select(ExternalItem).where(ExternalItem.canonical_identity == identity))
    if row is not None:
        return row
    row = ExternalItem(
        id=uid(),
        canonical_identity=identity,
        provider=item.provider,
        title=item.title,
        normalized_title=normalize_text(item.title),
        canonical_url=canonical_url(item.source_url),
        published_at=item.published_at,
        retrieved_at=item.retrieved_at,
        processing_version="1",
        raw_item_id=raw.id,
        created_at=item.retrieved_at,
    )
    session.add(row)
    session.flush()
    return row


def link_duplicate(
    session: Session,
    canonical_item: ExternalItem,
    duplicate_item: ExternalItem,
    relationship_type: str,
    score: float,
    evaluated_at,
) -> ExternalDuplicateLink:
    row = ExternalDuplicateLink(
        id=uid(),
        canonical_item_id=canonical_item.id,
        duplicate_item_id=duplicate_item.id,
        relationship_type=relationship_type,
        similarity_score=score,
        rule_version="1",
        evaluated_at=evaluated_at,
    )
    session.add(row)
    session.flush()
    return row


def add_alias(
    session: Session,
    entity_type: str,
    entity_id: str,
    alias: str,
    valid_from,
    alias_type: str = "symbol",
    source: str = "manual",
    priority: int = 1,
) -> ExternalEntityAlias:
    row = ExternalEntityAlias(
        id=uid(),
        entity_type=entity_type,
        entity_id=entity_id,
        alias=alias,
        normalized_alias=normalize_text(alias),
        alias_type=alias_type,
        source=source,
        priority=priority,
        valid_from=valid_from,
        is_active=True,
    )
    session.add(row)
    session.flush()
    return row


def resolve_alias(
    session: Session, entity_type: str, text: str, evaluated_at
) -> ExternalEntityAlias | None:
    normalized = normalize_text(text)
    return session.scalar(
        select(ExternalEntityAlias)
        .where(
            ExternalEntityAlias.entity_type == entity_type,
            ExternalEntityAlias.normalized_alias == normalized,
            ExternalEntityAlias.is_active.is_(True),
            ExternalEntityAlias.valid_from <= evaluated_at,
            (
                ExternalEntityAlias.valid_to.is_(None)
                | (ExternalEntityAlias.valid_to > evaluated_at)
            ),
        )
        .order_by(ExternalEntityAlias.priority.desc())
    )


def map_item_alias(
    session: Session,
    item: ExternalItem,
    alias: ExternalEntityAlias,
    evaluated_at,
    relationship_type: str = "primary_subject",
) -> ExternalEntityMapping:
    row = ExternalEntityMapping(
        id=uid(),
        external_item_id=item.id,
        entity_type=alias.entity_type,
        entity_id=alias.entity_id,
        relationship_type=relationship_type,
        mapping_method="exact_alias",
        mapping_score=1,
        matched_text=alias.alias,
        alias_id=alias.id,
        is_primary=relationship_type == "primary_subject",
        rule_version="1",
        created_at=evaluated_at,
    )
    session.add(row)
    session.flush()
    return row


def assess_readiness(
    session: Session,
    provider: str,
    evaluated_at,
    available: bool,
    last_received_at=None,
    freshness_seconds: int = 900,
) -> ExternalIntelligenceReadiness:
    from datetime import timedelta

    blocking = [] if available else ["provider_unavailable"]
    if (
        last_received_at is None
        or (evaluated_at - last_received_at).total_seconds() > freshness_seconds
    ):
        blocking.append("provider_stale")
    row = ExternalIntelligenceReadiness(
        id=uid(),
        provider=provider,
        evaluated_at=evaluated_at,
        status="not_ready" if blocking else "ready",
        blocking_reasons=blocking,
        warning_reasons=[],
        expires_at=evaluated_at + timedelta(seconds=freshness_seconds),
    )
    session.add(row)
    session.flush()
    return row

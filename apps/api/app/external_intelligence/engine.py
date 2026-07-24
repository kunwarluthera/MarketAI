from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

PROVIDERS = {
    "NEWSAPI": {"type": "news_api", "credential": "NEWS_API_KEY"},
    "GNEWS": {"type": "news_aggregator", "credential": "GNEWS_API_KEY"},
}


@dataclass(frozen=True)
class ProviderItem:
    provider: str
    provider_item_id: str | None
    title: str
    description: str | None
    source_url: str
    published_at: datetime
    retrieved_at: datetime
    raw_payload: dict


def normalize_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def canonical_url(value: str) -> str:
    parts = urlsplit(value)
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query)
        if not k.lower().startswith(("utm_", "fbclid", "gclid"))
    ]
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            urlencode(sorted(query)),
            "",
        )
    )


def canonical_identity(item: ProviderItem) -> str:
    basis = (
        item.provider_item_id
        or canonical_url(item.source_url)
        or f"{normalize_text(item.title)}|{item.published_at.isoformat()}"
    )
    return hashlib.sha256(basis.encode()).hexdigest()


def title_similarity(left: str, right: str) -> float:
    a, b = set(normalize_text(left).split()), set(normalize_text(right).split())
    return len(a & b) / len(a | b) if a | b else 1.0


def credentials_available(value: str | None) -> bool:
    return bool(value and value.strip())


def classify(title: str, description: str | None = None) -> dict:
    text = normalize_text(f"{title} {description or ''}")
    if any(term in text for term in ("denies", "false report", "no plans")):
        return {
            "category": "rumour",
            "impact": "unknown",
            "confirmation": "denied",
            "rule_version": "1",
        }
    if any(term in text for term in ("wins order", "awarded contract", "receives order")):
        return {
            "category": "order_win",
            "impact": "positive",
            "confirmation": "reported",
            "rule_version": "1",
        }
    return {
        "category": "unknown",
        "impact": "unknown",
        "confirmation": "unknown",
        "rule_version": "1",
    }


def assess_importance(
    category: str,
    relationship: str = "mentioned_only",
    source_tier: int = 1,
    confirmation: str = "unknown",
) -> dict:
    direct = relationship in {"primary_subject", "directly_affected"}
    material = category in {
        "acquisition",
        "merger",
        "bankruptcy",
        "regulatory_action",
        "order_win",
        "fraud",
    }
    level = (
        "high"
        if direct and material and confirmation in {"confirmed", "reported"}
        else "medium"
        if direct or material
        else "low"
    )
    return {
        "level": level,
        "rule_version": "1",
        "signals": {
            "direct": direct,
            "material_category": material,
            "source_tier": source_tier,
            "confirmation": confirmation,
        },
    }


SOURCE_CREDIBILITY = {
    "official": 3,
    "regulator": 3,
    "established_publication": 2,
    "aggregator": 1,
    "unknown": 0,
}


def source_tier(source_type: str) -> int:
    return SOURCE_CREDIBILITY.get(source_type, 0)


def confirmation_state(source_type: str, denied: bool = False) -> str:
    if denied:
        return "denied"
    return (
        "confirmed"
        if source_type in {"official", "regulator"}
        else "reported"
        if source_type == "established_publication"
        else "unknown"
    )

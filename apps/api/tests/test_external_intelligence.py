from datetime import UTC, datetime
from app.external_intelligence.engine import (
    ProviderItem,
    canonical_identity,
    canonical_url,
    classify,
    assess_importance,
    normalize_text,
    title_similarity,
)


def item(**kwargs):
    return ProviderItem(
        provider="NEWSAPI",
        provider_item_id=None,
        title=" Company <b>Wins</b> Order ",
        description="x",
        source_url="HTTPS://Example.com/a/?utm_source=x",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        retrieved_at=datetime(2026, 1, 1, 1, tzinfo=UTC),
        raw_payload={},
    )


def test_normalization_and_identity_are_stable():
    assert normalize_text(" A   B ") == "a b"
    assert canonical_url("https://Example.com/a/?utm_source=x") == "https://example.com/a"
    assert canonical_identity(item()) == canonical_identity(item())


def test_deterministic_title_similarity():
    assert title_similarity("Company wins order", "Company wins order") == 1.0
    assert title_similarity("Company wins order", "Different event") == 0.0


def test_negation_and_order_classification_are_deterministic():
    assert classify("Company wins order")["category"] == "order_win"
    denied = classify("Company denies order rumour")
    assert denied["category"] == "rumour"
    assert denied["confirmation"] == "denied"
    assert assess_importance("order_win", "primary_subject", 2, "reported")["level"] == "high"


def test_processing_lineage_is_stable():
    article = item()
    identity = canonical_identity(article)
    classification = classify(article.title, article.description)
    importance = assess_importance(
        classification["category"], "primary_subject", 2, classification["confirmation"]
    )
    assert identity == canonical_identity(article)
    assert classification["rule_version"] == "1"
    assert importance["rule_version"] == "1"
    assert set(importance["signals"]) == {
        "direct",
        "material_category",
        "source_tier",
        "confirmation",
    }

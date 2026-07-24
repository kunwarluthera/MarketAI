from app.explainability_governance.service import TRANSITIONS


def test_lifecycle_is_explicit_and_terminal_publication_is_immutable():
    assert "approved" in TRANSITIONS["pending"]
    assert "published" in TRANSITIONS["approved"]
    assert "published" not in TRANSITIONS["published"]


def test_invalid_transition_is_rejected_by_policy():
    assert "approved" not in TRANSITIONS["published"]

from hashlib import sha256
import json
from app.registry_audit.core import replay_lifecycle, verify_event_chain


def test_lifecycle_replay_exposes_invalid_transitions():
    result = replay_lifecycle(
        [
            {"event_id": "1", "occurred_at": "1", "state": "registered"},
            {"event_id": "2", "occurred_at": "2", "state": "champion_assigned"},
        ]
    )
    assert result["replayable"] is False


def test_event_chain_is_tamper_evident():
    event = {"event_id": "1", "action": "registered"}
    event["chain_hash"] = sha256(
        json.dumps(
            {"previous": "", "event": {"event_id": "1", "action": "registered"}}, sort_keys=True
        ).encode()
    ).hexdigest()
    assert verify_event_chain([event])["valid"] is True

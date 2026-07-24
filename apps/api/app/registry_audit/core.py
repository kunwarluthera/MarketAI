from hashlib import sha256
import json


VALID_TRANSITIONS = {
    "registered": {"promotion_requested"},
    "promotion_requested": {"approved_for_promotion", "rejected_for_promotion"},
    "approved_for_promotion": {"champion_assigned", "challenger_assigned"},
}


def verify_event_chain(events: list[dict]) -> dict:
    previous = ""
    findings = []
    for event in events:
        unsigned = {key: value for key, value in event.items() if key != "chain_hash"}
        expected = sha256(
            json.dumps({"previous": previous, "event": unsigned}, sort_keys=True).encode()
        ).hexdigest()
        if event.get("chain_hash") != expected:
            findings.append({"code": "EVENT_CHAIN_MISMATCH", "event_id": event.get("event_id")})
        previous = event.get("chain_hash", "")
    return {"valid": not findings, "findings": findings, "event_count": len(events)}


def replay_lifecycle(events: list[dict]) -> dict:
    state = "unregistered"
    findings = []
    for event in sorted(
        events, key=lambda item: (item.get("occurred_at", ""), item.get("event_id", ""))
    ):
        target = event.get("state")
        if state != "unregistered" and target not in VALID_TRANSITIONS.get(state, set()):
            findings.append({"code": "INVALID_TRANSITION", "from": state, "to": target})
        state = target
    return {"final_state": state, "findings": findings, "replayable": not findings}

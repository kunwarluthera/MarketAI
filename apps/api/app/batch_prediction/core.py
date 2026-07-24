from __future__ import annotations

import hashlib
import json


def checksum(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


ALLOWED_TRANSITIONS = {
    "created": {"eligible", "ineligible"},
    "eligible": {"materializing"},
    "materializing": {"planned", "ineligible"},
    "planned": {"queued"},
    "queued": {"running", "cancelled"},
    "running": {"completed", "partially_completed", "failed", "cancelled"},
}


def transition(current: str, target: str) -> None:
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"invalid_batch_transition:{current}:{target}")


def ordered_members(universe: dict) -> list[dict]:
    members = universe.get("members", [])
    if not isinstance(members, list):
        raise ValueError("malformed_universe")
    normalized = []
    for member in members:
        if not isinstance(member, dict) or not str(member.get("symbol", "")).strip():
            raise ValueError("invalid_universe_member")
        normalized.append(member)
    return sorted(
        normalized,
        key=lambda x: (
            str(x.get("symbol", "")).upper(),
            str(x.get("as_of_timestamp", "")),
            str(x.get("source_id", "")),
        ),
    )


def retry_decision(
    attempt_number: int, maximum_attempts: int, failure_code: str, retryable_codes: set[str]
) -> dict:
    retryable = failure_code in retryable_codes and attempt_number < maximum_attempts
    return {
        "retryable": retryable,
        "terminal": not retryable,
        "next_delay_seconds": (2 ** max(attempt_number - 1, 0)) if retryable else None,
    }

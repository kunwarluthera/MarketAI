from datetime import UTC, datetime
from hashlib import sha256
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.common.models import ModelRoleAssignment
from app.champion_challenger.core import RolePolicy, validate_assignments


def persist_assignment(
    session: Session, scope: str, champion: str | None, challengers: list[str], policy: RolePolicy
) -> dict:
    errors = validate_assignments(champion, challengers, policy)
    if errors:
        return {"assigned": False, "errors": list(errors), "registry_only": True}
    payload = {
        "scope": scope,
        "champion_identity": champion,
        "challenger_identities": challengers,
        "registry_only": True,
    }
    identity = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    if (
        session.scalar(
            select(ModelRoleAssignment).where(ModelRoleAssignment.assignment_identity == identity)
        )
        is None
    ):
        session.add(
            ModelRoleAssignment(
                assignment_identity=identity,
                scope=scope,
                champion_identity=champion,
                challenger_identities=challengers,
                status="active",
                payload=payload,
                created_at=datetime.now(UTC),
            )
        )
    return {"assigned": True, "assignment_identity": identity, **payload}

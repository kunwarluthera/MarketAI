from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.models import OpportunityRule


def register_rule(
    session: Session,
    *,
    code: str,
    display_name: str,
    description: str,
    category: str,
    version: str,
    parameters: dict,
) -> OpportunityRule:
    row = session.scalar(
        select(OpportunityRule).where(
            OpportunityRule.rule_code == code, OpportunityRule.rule_version == version
        )
    )
    if row is None:
        row = OpportunityRule(
            rule_code=code,
            display_name=display_name,
            description=description,
            category=category,
            rule_version=version,
            parameters=parameters,
            enabled=True,
            valid_from=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        session.add(row)
    return row

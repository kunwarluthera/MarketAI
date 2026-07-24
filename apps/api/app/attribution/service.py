from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.attribution.core import attribute, checksum, resolve_algorithm_contract
from app.common.models import (
    AttributionPolicy,
    LocalAttribution,
    LocalExplanation,
    ExplainabilityManifest,
)


def create_attribution(
    session: Session,
    explainability_id: str,
    prediction_identity: str,
    model_family: str,
    features: list[dict],
) -> dict:
    policy = session.scalar(
        select(AttributionPolicy).where(
            AttributionPolicy.policy_code == "CONTROLLED_LOCAL_ATTRIBUTION_V1"
        )
    )
    if policy is None or not policy.enabled:
        raise ValueError("policy_disabled")
    algorithm_contract = resolve_algorithm_contract(
        model_family, (policy.algorithm_priority or {}).get("algorithms")
    )
    algorithm = algorithm_contract["algorithm"]
    contributions = attribute(features, bool(policy.normalize_scores), policy.precision_digits)
    identity = checksum(
        {
            "explainability": explainability_id,
            "prediction": prediction_identity,
            "algorithm": algorithm_contract,
            "contributions": contributions,
        }
    )
    existing = session.scalar(
        select(LocalExplanation).where(LocalExplanation.explanation_identity == identity)
    )
    if existing:
        return {"explanation_identity": identity, "checksum": existing.checksum, "idempotent": True}
    explanation_payload = {"contributions": contributions, "algorithm": algorithm_contract}
    session.add(
        LocalExplanation(
            explanation_identity=identity,
            explainability_id=explainability_id,
            prediction_identity=prediction_identity,
            algorithm=algorithm,
            payload=explanation_payload,
            checksum=identity,
            created_at=datetime.now(UTC),
        )
    )
    manifest = session.scalar(
        select(ExplainabilityManifest).where(
            ExplainabilityManifest.explainability_id == explainability_id
        )
    )
    if manifest is not None:
        manifest.payload = {
            **manifest.payload,
            "local_explanation_identity": identity,
            "algorithm": algorithm_contract,
        }
    for row in contributions:
        session.add(
            LocalAttribution(
                explanation_identity=identity,
                feature_name=row["feature_name"],
                feature_index=row["feature_index"],
                payload=row,
                created_at=datetime.now(UTC),
            )
        )
    return {
        "explanation_identity": identity,
        "checksum": identity,
        "algorithm": algorithm,
        "idempotent": False,
    }

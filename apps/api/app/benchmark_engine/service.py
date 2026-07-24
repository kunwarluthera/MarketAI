from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.benchmark_engine.core import compare
from app.common.models import BenchmarkPolicy, BenchmarkComparison


def run_benchmark(
    session: Session,
    left_model: str,
    right_model: str,
    dataset_id: str,
    left_metrics: dict,
    right_metrics: dict,
) -> dict:
    policy = session.scalar(
        select(BenchmarkPolicy).where(BenchmarkPolicy.policy_code == "CONTROLLED_BENCHMARK_V1")
    )
    if policy is None or not policy.enabled:
        raise ValueError("policy_disabled")
    result = compare(left_metrics, right_metrics, dataset_id, dataset_id)
    identity = result["checksum"]
    if session.scalar(
        select(BenchmarkComparison).where(BenchmarkComparison.benchmark_id == identity)
    ):
        return {"benchmark_id": identity, **result, "idempotent": True}
    session.add(
        BenchmarkComparison(
            benchmark_id=identity,
            left_model=left_model,
            right_model=right_model,
            dataset_id=dataset_id,
            payload=result,
            checksum=identity,
            created_at=datetime.now(UTC),
        )
    )
    return {"benchmark_id": identity, **result, "idempotent": False}

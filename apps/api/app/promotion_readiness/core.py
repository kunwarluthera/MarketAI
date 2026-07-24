from app.attribution.core import checksum


def evaluate(evidence: dict, required: list[str]) -> dict:
    completed = sorted(key for key in required if evidence.get(key) is True)
    missing = sorted(set(required) - set(completed))
    status = "READY_FOR_REVIEW" if not missing else "NOT_READY"
    scorecard = {"completed": completed, "missing": missing, "status": status}
    return {"scorecard": scorecard, "checksum": checksum(scorecard)}

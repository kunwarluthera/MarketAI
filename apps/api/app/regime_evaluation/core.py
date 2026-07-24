from app.attribution.core import checksum


def evaluate(groups: dict[str, list[float]], minimum_samples: int = 1) -> dict:
    if any(len(values) < minimum_samples for values in groups.values()):
        raise ValueError("minimum_samples")
    summaries = {
        name: {
            "sample_count": len(values),
            "mean": sum(values) / len(values),
            "variance": (
                sum((value - sum(values) / len(values)) ** 2 for value in values) / len(values)
                if values
                else 0.0
            ),
        }
        for name, values in sorted(groups.items())
    }
    return {
        "groups": summaries,
        "coverage": {
            "group_count": len(groups),
            "sample_count": sum(len(v) for v in groups.values()),
        },
        "checksum": checksum(summaries),
    }

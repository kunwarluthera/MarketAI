from app.attribution.core import checksum


def compare(left: dict, right: dict, dataset_left: str, dataset_right: str) -> dict:
    if dataset_left != dataset_right:
        raise ValueError("dataset_incompatible")
    keys = sorted(set(left) | set(right))
    deltas = {
        key: (right.get(key, 0) - left.get(key, 0))
        for key in keys
        if isinstance(right.get(key, left.get(key)), (int, float))
    }
    return {
        "deltas": deltas,
        "dataset_compatible": True,
        "checksum": checksum({"left": left, "right": right, "deltas": deltas}),
    }

import hashlib
import json

import pytest

from app.model_loading.core import LoadPolicy, load_callable_handle


def artifact(payload: dict) -> tuple[bytes, str]:
    raw = json.dumps(payload).encode()
    return raw, hashlib.sha256(raw).hexdigest()


def test_approved_callable_contract_is_deterministic():
    raw, digest = artifact({"inference_enabled": True, "operation": "identity"})
    contract = load_callable_handle(raw, digest, "json_manifest", "v1", LoadPolicy("p", "1"))
    assert contract.predict([{"value": 1}, {"value": 2}]) == [1, 2]


def test_unapproved_operation_is_rejected():
    raw, digest = artifact({"inference_enabled": True, "operation": "python:eval"})
    with pytest.raises(ValueError, match="allowlisted"):
        load_callable_handle(raw, digest, "json_manifest", "v1", LoadPolicy("p", "1"))

import hashlib
import json
import pytest
from app.model_loading.core import LoadPolicy, load_handle


def test_loading_requires_checksum_and_returns_opaque_handle():
    raw = json.dumps({"model_family": "baseline", "inference_enabled": False}).encode()
    checksum = hashlib.sha256(raw).hexdigest()
    handle = load_handle(raw, checksum, "json_manifest", "version-1", LoadPolicy("safe", "1"))
    assert handle.version_identity == "version-1"
    assert not hasattr(handle, "predict")


def test_inference_enabled_artifact_is_rejected():
    raw = json.dumps({"inference_enabled": True}).encode()
    with pytest.raises(ValueError):
        load_handle(
            raw, hashlib.sha256(raw).hexdigest(), "json_manifest", "v", LoadPolicy("safe", "1")
        )

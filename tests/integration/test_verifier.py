import json

def test_verify_snapshot_chain(verifier):
    chain = [
        {"snapshot_id": "h1", "prev_hash": None},
        {"snapshot_id": "h2", "prev_hash": "h1"},
    ]
    assert verifier.verify_snapshot_chain(chain)["valid"] is True

def test_verify_broken_chain(verifier):
    chain = [
        {"snapshot_id": "h1", "prev_hash": None},
        {"snapshot_id": "h2", "prev_hash": "invalid_hash"},
    ]
    assert verifier.verify_snapshot_chain(chain)["valid"] is False

def test_verify_telemetry_bundle(verifier, tmp_path):
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps({
        "agent_id": "x", "fingerprint": "y", "timestamp": 1.0,
        "capabilities": {}, "schema_version": "1.0"
    }))
    assert verifier.verify_telemetry_bundle(bundle)["valid"] is True

def test_verify_bridge_artifact(verifier):
    bridge = {
        "bridge_id": "fake",
        "agent_id": "a",
        "expected_signature": {},
        "actual_signature": {},
        "adapter_code": ""
    }
    # It should fail validation because 'fake' is not the real hash
    res = verifier.verify_bridge_artifact(bridge)
    assert res["valid"] is False
    assert "recomputed" in res

def test_verify_valid_bridge_artifact(verifier):
    import hashlib
    agent_id = "a"
    exp = {}
    act = {}
    code = "def bridge_adapter(actual_fn, **kwargs):\n    return actual_fn()"
    recomputed = hashlib.sha256(f"{agent_id}:{exp}:{act}:{code}".encode()).hexdigest()
    
    bridge = {
        "bridge_id": recomputed,
        "agent_id": agent_id,
        "expected_signature": exp,
        "actual_signature": act,
        "adapter_code": code
    }
    res = verifier.verify_bridge_artifact(bridge)
    assert res["valid"] is True

def test_verify_bridge_artifact_missing_fields(verifier):
    bridge = {
        "bridge_id": "fake",
        "agent_id": "a"
        # missing expected_signature, actual_signature, adapter_code
    }
    res = verifier.verify_bridge_artifact(bridge)
    assert res["valid"] is False
    assert "missing" in res
    assert "adapter_code" in res["missing"]

def test_verify_telemetry_bundle_missing_fields(verifier, tmp_path):
    bundle = tmp_path / "bundle_missing.json"
    bundle.write_text(json.dumps({
        "agent_id": "x", "fingerprint": "y"
        # missing timestamp, capabilities, schema_version
    }))
    res = verifier.verify_telemetry_bundle(bundle)
    assert res["valid"] is False
    assert "missing" in res
    assert "timestamp" in res["missing"]

def test_verify_empty_snapshot_chain(verifier):
    assert verifier.verify_snapshot_chain([])["valid"] is True


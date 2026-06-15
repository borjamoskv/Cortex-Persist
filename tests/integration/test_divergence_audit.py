def test_divergence_no_diff(auditor):
    exp = {"routes": {"a": "sig_a"}, "capabilities": ["c1"]}
    act = {"routes": {"a": "sig_a"}, "capabilities": ["c1"]}
    report = auditor.build_report("a1", "obs_fp", "exp_fp", exp, act, 1.0)
    assert not report.route_deltas
    assert report.severity == "ok"

def test_divergence_missing_route(auditor):
    exp = {"routes": {"a": "sig_a", "b": "sig_b"}}
    act = {"routes": {"a": "sig_a"}}
    report = auditor.build_report("a1", "obs", "exp", exp, act, 1.0)
    assert any(d["type"] == "missing_route" and d["route"] == "b" for d in report.route_deltas)
    assert report.severity == "high"

def test_divergence_signature_mismatch(auditor):
    exp = {"routes": {"a": "sig_a"}}
    act = {"routes": {"a": "sig_b"}}
    report = auditor.build_report("a1", "obs", "exp", exp, act, 1.0)
    assert any(d["type"] == "route_signature_mismatch" and d["route"] == "a" for d in report.route_deltas)
    assert report.severity == "high"

def test_divergence_extra_route(auditor):
    exp = {"routes": {"a": "sig_a"}}
    act = {"routes": {"a": "sig_a", "b": "sig_b"}}
    report = auditor.build_report("a1", "obs", "exp", exp, act, 1.0)
    assert any(d["type"] == "unexpected_route" and d["route"] == "b" for d in report.route_deltas)
    assert report.severity == "low"

def test_divergence_missing_capability(auditor):
    exp = {"capabilities": ["c1", "c2"]}
    act = {"capabilities": ["c1"]}
    report = auditor.build_report("a1", "obs", "exp", exp, act, 1.0)
    assert any(d["type"] == "missing_capability" and d["capability"] == "c2" for d in report.route_deltas)
    assert report.severity == "medium"

def test_divergence_extra_capability(auditor):
    exp = {"capabilities": ["c1"]}
    act = {"capabilities": ["c1", "c2"]}
    report = auditor.build_report("a1", "obs", "exp", exp, act, 1.0)
    assert any(d["type"] == "unexpected_capability" and d["capability"] == "c2" for d in report.route_deltas)
    assert report.severity == "low"

def test_divergence_report_proof_hash(auditor):
    exp = {"routes": {"a": "sig_a"}}
    act = {"routes": {"a": "sig_b"}}
    report = auditor.build_report("a1", "obs", "exp", exp, act, 1.0)
    assert isinstance(report.proof_hash, str)
    assert len(report.proof_hash) == 64
    # Recomputing the hash should match report.proof_hash
    import hashlib
    import json
    payload = {
        "agent_id": report.agent_id,
        "observed_fingerprint": report.observed_fingerprint,
        "expected_fingerprint": report.expected_fingerprint,
        "route_deltas": report.route_deltas,
        "severity": report.severity,
        "timestamp": report.timestamp,
    }
    proof_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    expected_hash = hashlib.sha256(proof_payload.encode()).hexdigest()
    assert report.proof_hash == expected_hash


import os
import json
import pytest


def test_vsa_ledger_hash_and_commit(tmp_path, monkeypatch):
    """Verify HyperVector SHA-256 hash generation and EpistemicMembrane ledger commits."""
    # Isolate tests to a clean temp directory to prevent global filesystem contamination
    monkeypatch.chdir(tmp_path)

    import cortex_rs

    # 1. Verify HyperVector hashing
    hv = cortex_rs.HyperVector.random(256)
    hv_hash = hv.hash()

    assert isinstance(hv_hash, str)
    assert len(hv_hash) == 64  # SHA-256 is 64 hex characters
    assert all(c in "0123456789abcdef" for c in hv_hash)

    # Determinism check
    assert hv.hash() == hv_hash

    # 2. Verify EpistemicMembrane commit
    membrane = cortex_rs.EpistemicMembrane(256)
    committed_hash = membrane.commit(hv)
    assert committed_hash == hv_hash

    # 3. Verify C5-REAL cryptographic append-only ledger entry
    ledger_path = tmp_path / "cortex_ledger.jsonl"
    assert ledger_path.is_file()

    with open(ledger_path) as f:
        lines = f.readlines()

    assert len(lines) == 1
    entry = json.loads(lines[0].strip())

    assert entry["hash"] == hv_hash
    assert entry["dim"] == 256
    assert isinstance(entry["timestamp"], int | float)

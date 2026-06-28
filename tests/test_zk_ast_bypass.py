# [C5-REAL] Exergy-Maximized
"""
Unit tests for the ZKSwarmGuard formal verification & fast-path eligibility.
"""

import pytest
from cortex.guards.zk_guard import ZKSwarmGuard, VoidStateSecurityError


@pytest.fixture
def mock_zk_swarm_identity(monkeypatch):
    """Mocks ZKSwarmIdentity verification to bypass keypair requirements in unit tests."""
    class MockIdentity:
        @staticmethod
        def verify_payload(content: str, public_key_b64: str, signature_b64: str) -> bool:
            # Simple rule: if signature has "invalid", fail. Otherwise pass.
            return "invalid" not in signature_b64

    monkeypatch.setattr("cortex.guards.zk_guard.ZKSwarmIdentity", MockIdentity)


async def test_zk_guard_non_enforced_types():
    # Types not in enforcement whitelist should immediately bypass
    guard = ZKSwarmGuard(enforce_on_types=("decision", "rule", "code"))
    is_fast = await guard.verify_integrity("some content", "knowledge", {})
    assert is_fast is False


async def test_zk_guard_missing_proofs_on_enforced_types():
    guard = ZKSwarmGuard(enforce_on_types=("decision",))
    with pytest.raises(VoidStateSecurityError, match="Missing cryptographic proof"):
        await guard.verify_integrity("some content", "decision", {})


async def test_zk_guard_invalid_signature(mock_zk_swarm_identity):
    guard = ZKSwarmGuard(enforce_on_types=("decision",))
    meta = {
        "agent_public_key": "some_pubkey",
        "zk_proof_signature": "invalid_sig"
    }
    with pytest.raises(VoidStateSecurityError, match="signature INVALID"):
        await guard.verify_integrity("some content", "decision", meta)


async def test_zk_guard_valid_signature_no_fast_path(mock_zk_swarm_identity):
    guard = ZKSwarmGuard(enforce_on_types=("decision",))
    meta = {
        "agent_public_key": "some_pubkey",
        "zk_proof_signature": "valid_sig"
    }
    # No formal_correctness_proof in metadata, so not Fast-Path eligible
    is_fast = await guard.verify_integrity("some content", "decision", meta)
    assert is_fast is False


async def test_zk_guard_fast_path_eligible(mock_zk_swarm_identity):
    guard = ZKSwarmGuard(enforce_on_types=("decision",))
    meta = {
        "agent_public_key": "some_pubkey",
        "zk_proof_signature": "valid_sig",
        "formal_correctness_proof": "valid_ast_proof"
    }
    # Both valid signature and formal proof present -> Fast-Path eligible
    is_fast = await guard.verify_integrity("some content", "decision", meta)
    assert is_fast is True

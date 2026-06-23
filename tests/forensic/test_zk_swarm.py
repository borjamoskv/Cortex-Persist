# [C5-REAL] Exergy-Maximized
"""
Forensic Test Suite for ZK-Swarm Cryptographic Architecture.

Provides mathematically enforced assertions over the CORTEX Void-State Security primitives.
Ensures generation, execution proof signing, and Byzantine rejection of hallucinated facts.
"""

import pytest

from babylon60.crypto.keys import ZKSwarmIdentity
from babylon60.guards.zk_guard import VoidStateSecurityError, ZKSwarmGuard


@pytest.fixture
def agent_keypair():
    """Generates a fresh keypair for isolated test assertions."""
    return ZKSwarmIdentity.generate_keypair()


@pytest.mark.asyncio
async def test_zk_swarm_identity_signing_cycle(agent_keypair):
    """AXIOM T-003: Signature determinism over state deltas."""
    payload = '{"action": "sell", "asset": "MKR", "confidence": 0.99}'

    # 1. Agent signs the proposed delta
    signature_b64 = ZKSwarmIdentity.sign_payload(payload, agent_keypair.private_key_b64)
    assert isinstance(signature_b64, str)
    assert len(signature_b64) > 40

    # 2. Guard mathematically verifies the signature
    is_valid = ZKSwarmIdentity.verify_payload(
        content=payload, public_key_b64=agent_keypair.public_key_b64, signature_b64=signature_b64
    )
    assert is_valid is True

    # 3. Byzantine test: modifying the payload post-signature must fail
    is_valid_byzantine = ZKSwarmIdentity.verify_payload(
        content='{"action": "buy", "asset": "MKR", "confidence": 0.99}',
        public_key_b64=agent_keypair.public_key_b64,
        signature_b64=signature_b64,
    )
    assert is_valid_byzantine is False


@pytest.mark.asyncio
async def test_zk_guard_enforcement_on_high_rigor_types(agent_keypair):
    """Ensures structural BFT validation across inference topological limits."""
    guard = ZKSwarmGuard(enforce_on_types=("decision", "rule", "code"))
    payload = "def execute_flashloan(): pass"

    # Validation 1: Rejection due to missing proof
    with pytest.raises(VoidStateSecurityError) as exc_info:
        await guard.verify_integrity(content=payload, fact_type="code", meta={})
    assert "Missing cryptographic proof" in str(exc_info.value)

    # Validation 2: Rejection due to spoofed signature
    with pytest.raises(VoidStateSecurityError) as exc_info:
        await guard.verify_integrity(
            content=payload,
            fact_type="decision",
            meta={
                "agent_public_key": agent_keypair.public_key_b64,
                "zk_proof_signature": "Fake_Spoofed_Signature_1234==",
            },
        )
    assert "INVALID" in str(exc_info.value)
    assert "hallucination" in str(exc_info.value)

    # Validation 3: Successful acceptance of cryptographically sound payload
    signature = ZKSwarmIdentity.sign_payload(payload, agent_keypair.private_key_b64)
    result = await guard.verify_integrity(
        content=payload,
        fact_type="decision",
        meta={"agent_public_key": agent_keypair.public_key_b64, "zk_proof_signature": signature},
    )
    assert result is None  # Should pass cleanly without raising

    # Validation 4: Passive memory ("knowledge") bypasses the guard constraint
    result_knowledge = await guard.verify_integrity(
        content="General background information", fact_type="knowledge", meta={}
    )
    assert result_knowledge is None

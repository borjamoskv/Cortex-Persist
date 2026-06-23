# [C5-REAL] Exergy-Maximized
import pytest
from babylon60.consensus.babylon_quorum import BabylonQuorum
from babylon60.crypto.keys import ZKSwarmIdentity

def test_babylon_quorum_mock_fallback():
    """Verify that reach_consensus defaults to simulation when no signatures are provided."""
    quorum = BabylonQuorum(required_signatures=3)
    # 64-character dummy proof hash
    dummy_hash = "a" * 64
    success, commit_hash = quorum.reach_consensus(dummy_hash, {"test": "data"})
    assert success is True
    assert commit_hash is not None

def test_babylon_quorum_cryptographic_verification_success():
    """Verify consensus succeeds when threshold of valid cryptographic signatures is reached."""
    quorum = BabylonQuorum(required_signatures=2)
    proof_hash = "a" * 64

    # Generate keys and signatures for 2 peers
    peer1_keys = ZKSwarmIdentity.generate_keypair()
    peer2_keys = ZKSwarmIdentity.generate_keypair()

    quorum.register_peer("peer1", peer1_keys.public_key_b64)
    quorum.register_peer("peer2", peer2_keys.public_key_b64)

    sig1 = ZKSwarmIdentity.sign_payload(proof_hash, peer1_keys.private_key_b64)
    sig2 = ZKSwarmIdentity.sign_payload(proof_hash, peer2_keys.private_key_b64)

    signatures = [
        ("peer1", sig1),
        ("peer2", sig2)
    ]

    success, commit_hash = quorum.reach_consensus(proof_hash, {"test": "data"}, signatures=signatures)
    assert success is True
    assert commit_hash is not None

def test_babylon_quorum_cryptographic_verification_failure_insufficient_sigs():
    """Verify consensus fails when there are fewer valid signatures than the required threshold."""
    quorum = BabylonQuorum(required_signatures=2)
    proof_hash = "a" * 64

    peer1_keys = ZKSwarmIdentity.generate_keypair()
    quorum.register_peer("peer1", peer1_keys.public_key_b64)

    sig1 = ZKSwarmIdentity.sign_payload(proof_hash, peer1_keys.private_key_b64)
    signatures = [("peer1", sig1)]  # Only 1 signature, threshold is 2

    success, commit_hash = quorum.reach_consensus(proof_hash, {"test": "data"}, signatures=signatures)
    assert success is False
    assert commit_hash is None

def test_babylon_quorum_cryptographic_verification_failure_invalid_sig():
    """Verify consensus fails if a signature is invalid or tampered with."""
    quorum = BabylonQuorum(required_signatures=1)
    proof_hash = "a" * 64

    peer1_keys = ZKSwarmIdentity.generate_keypair()
    quorum.register_peer("peer1", peer1_keys.public_key_b64)

    # Sign a DIFFERENT payload to generate an invalid signature
    sig1 = ZKSwarmIdentity.sign_payload("different_payload", peer1_keys.private_key_b64)
    signatures = [("peer1", sig1)]

    success, commit_hash = quorum.reach_consensus(proof_hash, {"test": "data"}, signatures=signatures)
    assert success is False
    assert commit_hash is None

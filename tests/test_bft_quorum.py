import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from babylon60.consensus.bft_quorum import BFTQuorumGuard


@pytest.fixture
def keys():
    return {
        "agent_1": ed25519.Ed25519PrivateKey.generate(),
        "agent_2": ed25519.Ed25519PrivateKey.generate(),
        "agent_3": ed25519.Ed25519PrivateKey.generate(),
        "agent_4": ed25519.Ed25519PrivateKey.generate(),
        "rogue_agent": ed25519.Ed25519PrivateKey.generate(),
    }


@pytest.fixture
def bft_guard(keys):
    known_peers = {k: v.public_key() for k, v in keys.items() if k != "rogue_agent"}
    return BFTQuorumGuard(known_peers)


def test_bft_quorum_met(bft_guard, keys):
    payload = b"CRDT_MUTATION_123"

    # 4 known peers -> N/3 = max(1, 4//3) = 1 required signature
    # Let's provide 2 valid signatures
    signatures = {
        "agent_1": keys["agent_1"].sign(payload),
        "agent_2": keys["agent_2"].sign(payload),
    }

    assert bft_guard.authorize_payload(payload, signatures) is True


def test_bft_quorum_not_met_insufficient(bft_guard, keys):
    payload = b"CRDT_MUTATION_456"

    # Provide 0 signatures -> Should fail
    signatures = {}

    assert bft_guard.authorize_payload(payload, signatures) is False


def test_bft_quorum_not_met_rogue(bft_guard, keys):
    payload = b"CRDT_MUTATION_789"

    # Rogue agent signs it. Even if signature matches the rogue's key,
    # the rogue is not in the known_peers registry.
    signatures = {
        "rogue_agent": keys["rogue_agent"].sign(payload),
    }

    assert bft_guard.authorize_payload(payload, signatures) is False


def test_bft_quorum_standalone():
    # Standalone fallback mode (0 peers known)
    guard = BFTQuorumGuard({})
    payload = b"STANDALONE_MUTATION"
    signatures = {}

    assert guard.authorize_payload(payload, signatures) is True

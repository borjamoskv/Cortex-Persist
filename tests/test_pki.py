import base64
import json
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from cortex.consensus.pki import TrustMatrix


@pytest.fixture
def pki():
    return TrustMatrix()


def test_pki_handshake_success(pki):
    # Host generates bootstrap token
    bootstrap_token = "BT-849302-XYZ"
    pki.authorize_bootstrap_token(bootstrap_token)

    # Agent generates ephemeral keys
    priv_key = ed25519.Ed25519PrivateKey.generate()
    pub_key = priv_key.public_key()

    pub_b64 = base64.b64encode(
        pub_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
    ).decode("ascii")

    agent_id = "agent_omega"

    # Agent signs the payload (agent_id:token)
    message = f"{agent_id}:{bootstrap_token}".encode()
    sig_b64 = base64.b64encode(priv_key.sign(message)).decode("ascii")

    # Create handshake payload
    payload = json.dumps(
        {
            "agent_id": agent_id,
            "public_key_b64": pub_b64,
            "bootstrap_token": bootstrap_token,
            "signature_b64": sig_b64,
        }
    )

    # Process handshake
    assert pki.process_handshake(payload) is True

    # Token should be burned
    assert bootstrap_token not in pki._valid_bootstrap_tokens

    # Peer should be registered
    known_peers = pki.get_known_peers()
    assert agent_id in known_peers


def test_pki_handshake_invalid_signature(pki):
    bootstrap_token = "BT-FAIL-SIG"
    pki.authorize_bootstrap_token(bootstrap_token)

    priv_key = ed25519.Ed25519PrivateKey.generate()
    pub_key = priv_key.public_key()
    pub_b64 = base64.b64encode(
        pub_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
    ).decode("ascii")

    agent_id = "agent_rogue"

    # Rogue signs the WRONG message
    message = f"fake_agent_id:{bootstrap_token}".encode()
    sig_b64 = base64.b64encode(priv_key.sign(message)).decode("ascii")

    payload = json.dumps(
        {
            "agent_id": agent_id,
            "public_key_b64": pub_b64,
            "bootstrap_token": bootstrap_token,
            "signature_b64": sig_b64,
        }
    )

    assert pki.process_handshake(payload) is False
    assert agent_id not in pki.get_known_peers()


def test_pki_revocation(pki):
    bootstrap_token = "BT-REVOKE"
    pki.authorize_bootstrap_token(bootstrap_token)

    priv_key = ed25519.Ed25519PrivateKey.generate()
    pub_b64 = base64.b64encode(
        priv_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
    ).decode("ascii")
    agent_id = "agent_revoked"

    message = f"{agent_id}:{bootstrap_token}".encode()
    sig_b64 = base64.b64encode(priv_key.sign(message)).decode("ascii")

    payload = json.dumps(
        {
            "agent_id": agent_id,
            "public_key_b64": pub_b64,
            "bootstrap_token": bootstrap_token,
            "signature_b64": sig_b64,
        }
    )

    # Register
    assert pki.process_handshake(payload) is True

    # Revoke
    pki.revoke_agent(agent_id)
    assert agent_id not in pki.get_known_peers()
    assert agent_id in pki._revoked

    # Try to rejoin (even with a new token)
    new_token = "BT-REJOIN"
    pki.authorize_bootstrap_token(new_token)
    message2 = f"{agent_id}:{new_token}".encode()
    sig_b64_2 = base64.b64encode(priv_key.sign(message2)).decode("ascii")

    payload2 = json.dumps(
        {
            "agent_id": agent_id,
            "public_key_b64": pub_b64,
            "bootstrap_token": new_token,
            "signature_b64": sig_b64_2,
        }
    )

    assert pki.process_handshake(payload2) is False

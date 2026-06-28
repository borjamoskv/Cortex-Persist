import pytest
import base64
from cortex.crypto.keys import KeyManager, Signer, Verifier


@pytest.fixture
def km(tmp_path, monkeypatch):
    monkeypatch.setenv("CORTEX_DB_PATH", str(tmp_path / "cortex.db"))
    # Use a test service name so it doesn't collide with the real OS keyring
    manager = KeyManager(service_name="cortex_test_enterprise")
    yield manager
    # Teardown: we could revoke keys if needed, but KeyManager relies on OS keyring,
    # so we might mock keyring in a real scenario. For now, we use a distinct service_name.


def test_key_manager_generate_and_retrieve(km):
    actor_id = "test_actor_1"

    # Clean up first in case it's lingering
    km.revoke_key(actor_id)

    public_key = km.generate_and_store_key(actor_id)
    assert public_key is not None
    assert isinstance(public_key, str)

    private_key = km.get_private_key_b64(actor_id)
    assert private_key is not None
    assert isinstance(private_key, str)

    # Verify we can decode it
    base64.b64decode(private_key)


def test_key_manager_revoke(km):
    actor_id = "test_actor_2"
    km.generate_and_store_key(actor_id)

    # Should exist
    assert km.get_private_key_b64(actor_id) is not None

    # Revoke it
    assert km.revoke_key(actor_id) is True
    assert km.is_revoked(actor_id) is True

    # Should not exist or be accessible
    assert km.get_private_key_b64(actor_id) is None


def test_signer_and_verifier(km):
    actor_id = "test_actor_3"
    km.revoke_key(actor_id)
    public_key = km.generate_and_store_key(actor_id)
    private_key = km.get_private_key_b64(actor_id)

    payload_hash = "abcdef123456"
    timestamp = "2026-06-26T00:00:00Z"

    # Sign
    signature = Signer.sign_payload(private_key, payload_hash, timestamp)
    assert signature is not None

    # Verify
    is_valid = Verifier.verify_signature(public_key, payload_hash, timestamp, signature)
    assert is_valid is True

    # Verify fails on tampered payload
    is_valid_tampered = Verifier.verify_signature(public_key, "tampered_hash", timestamp, signature)
    assert is_valid_tampered is False


def test_legacy_signing(km):
    actor_id = "test_actor_4"
    km.revoke_key(actor_id)
    public_key = km.generate_and_store_key(actor_id)
    private_key = km.get_private_key_b64(actor_id)

    content = '{"some": "raw_content"}'

    signature = Signer.sign_raw_content(private_key, content)
    assert signature is not None

    is_valid = Verifier.verify_raw_content(content, public_key, signature)
    assert is_valid is True

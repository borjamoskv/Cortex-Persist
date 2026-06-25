# [C5-REAL] Exergy-Maximized
"""Tests for CortexEncrypter strict mode and custom HKDF salt functionality."""

import os
import threading
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from legacy_research.crypto.aes import CortexEncrypter, get_default_encrypter, reset_default_encrypter
from legacy_research.utils.errors import DecryptionPolicyError

TEST_MASTER_KEY = b"1" * 32
ALT_MASTER_KEY = b"2" * 32


def test_strict_mode_rejects_plaintext():
    """Verify that decrypting plaintext raises DecryptionPolicyError in strict mode."""
    enc = CortexEncrypter(TEST_MASTER_KEY, strict_mode=True)
    with pytest.raises(DecryptionPolicyError, match="data lacks encryption prefix in strict mode"):
        enc.decrypt_str("unencrypted_plaintext")

    # In non-strict mode, it should fallback to plaintext silently
    enc_non_strict = CortexEncrypter(TEST_MASTER_KEY, strict_mode=False)
    assert enc_non_strict.decrypt_str("unencrypted_plaintext") == "unencrypted_plaintext"


def test_strict_mode_encryption_requires_active():
    """Verify that encrypting in strict mode raises RuntimeError if no master key is loaded."""
    enc = CortexEncrypter(None, strict_mode=True)
    with pytest.raises(
        RuntimeError,
        match="Strict crypto mode active: cannot encrypt data without a loaded Master Key.",
    ):
        enc.encrypt_str("plaintext")

    # In non-strict mode, it should return plaintext as-is
    enc_non_strict = CortexEncrypter(None, strict_mode=False)
    assert enc_non_strict.encrypt_str("plaintext") == "plaintext"


def test_custom_hkdf_salt():
    """Verify that a custom HKDF salt derivations are isolated from default salt derivations."""
    custom_salt = b"custom_isolation_salt_999"
    enc_default = CortexEncrypter(TEST_MASTER_KEY)
    enc_custom = CortexEncrypter(TEST_MASTER_KEY, hkdf_salt=custom_salt)

    plaintext = "super_secret_payload"
    tenant = "tenant-omega"

    ciphertext_default = enc_default.encrypt_str(plaintext, tenant_id=tenant)
    ciphertext_custom = enc_custom.encrypt_str(plaintext, tenant_id=tenant)

    # They must have different prefixes and ciphertexts
    assert ciphertext_default != ciphertext_custom

    # Decrypting default ciphertext with custom encrypter must fail
    with pytest.raises(ValueError, match="Decryption failed for tenant"):
        enc_custom.decrypt_str(ciphertext_default, tenant_id=tenant)

    # Decrypting custom ciphertext with default encrypter must fail
    with pytest.raises(ValueError, match="Decryption failed for tenant"):
        enc_default.decrypt_str(ciphertext_custom, tenant_id=tenant)

    # Decrypting own ciphertext succeeds
    assert enc_custom.decrypt_str(ciphertext_custom, tenant_id=tenant) == plaintext
    assert enc_default.decrypt_str(ciphertext_default, tenant_id=tenant) == plaintext


def test_singleton_thread_safety_and_reset():
    """Verify thread-safe lazy-initialization and resetting of default encrypter."""
    reset_default_encrypter()

    def get_instance():
        return get_default_encrypter()

    threads = []
    instances = []

    # Spawn 10 threads trying to obtain the default encrypter simultaneously
    for _ in range(10):
        t = threading.Thread(target=lambda: instances.append(get_instance()))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # All threads should have received the exact same instance
    first_instance = instances[0]
    assert all(inst is first_instance for inst in instances)

    # Resetting should clear it
    reset_default_encrypter()

    # Getting again should produce a new (but same across threads) instance
    new_instances = []
    threads = []
    for _ in range(10):
        t = threading.Thread(target=lambda: new_instances.append(get_instance()))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    first_new_instance = new_instances[0]
    assert all(inst is first_new_instance for inst in new_instances)
    assert first_new_instance is not first_instance

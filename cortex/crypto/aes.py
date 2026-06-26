# [C5-REAL] Exergy-Maximized
"""
AES-256-GCM Envelope Encryption.
Application-level encryption for L3 Ledgers.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import os
import threading
from typing import Any

from cryptography.exceptions import InvalidKey, InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from cortex.utils.errors import DecryptionPolicyError

logger = logging.getLogger("cortex.crypto")

_NONCE_LENGTH = 12  # 96-bit nonce for GCM
_KEY_LENGTH = 32  # 256-bit AES key


class CortexEncrypter:
    """Zero-Knowledge Data Encrypter for DB rows.
    Uses AES-GCM (Authenticated Encryption).
    """

    PREFIX = "v6_aesgcm:"

    def __init__(
        self,
        master_key: bytes | None,
        strict_mode: bool = False,
        hkdf_salt: bytes | None = None,
    ) -> None:
        if master_key is not None and len(master_key) != _KEY_LENGTH:
            raise ValueError(f"AES-256 requires a {_KEY_LENGTH}-byte master key.")
        self._master_key = master_key
        self.strict_mode = strict_mode
        if hkdf_salt is None:
            try:
                import cortex.core.config as config

                self.hkdf_salt = config.HKDF_SALT.encode("utf-8")
            except (ImportError, AttributeError):
                self.hkdf_salt = b"cortex_v6_tenant_isolation_salt"
        else:
            self.hkdf_salt = hkdf_salt
        # Cache of derived keys per tenant
        self._tenant_keys: dict[str, bytes] = {}

    @property
    def is_active(self) -> bool:
        return self._master_key is not None

    def _get_tenant_key(self, tenant_id: str) -> bytes:
        """Derive a tenant-specific 32-byte key using HKDF over the master key.
        This ensures Zero-Trust cryptographic isolation between tenants.
        """
        if not self.is_active:
            raise RuntimeError("Cannot derive key without a Master Key.")
        if tenant_id in self._tenant_keys:
            return self._tenant_keys[tenant_id]

        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=_KEY_LENGTH,
            salt=self.hkdf_salt,
            info=tenant_id.encode("utf-8"),
        )
        assert self._master_key is not None
        tenant_key = hkdf.derive(self._master_key)
        self._tenant_keys[tenant_id] = tenant_key
        return tenant_key

    def encrypt_str(self, data: str | None, tenant_id: str = "default") -> str | None:
        """Encrypt a string and return a safe Base64 representation.
        If data is None or empty, return as is.
        """
        if not data:
            return data
        if not self.is_active:
            if self.strict_mode:
                raise RuntimeError(
                    "Strict crypto mode active: cannot encrypt data without a loaded Master Key."
                )
            return data

        key = self._get_tenant_key(tenant_id)
        aesgcm = AESGCM(key)
        nonce = os.urandom(_NONCE_LENGTH)
        ciphertext = aesgcm.encrypt(nonce, data.encode("utf-8"), None)

        # We prepend a clear v6 prefix so we can detect it on decrypt
        combined = nonce + ciphertext
        return self.PREFIX + base64.b64encode(combined).decode("utf-8")

    def decrypt_str(self, encrypted_data: str | None, tenant_id: str = "default") -> str | None:
        """Decrypt a Base64 string back into plaintext."""
        if not encrypted_data:
            return encrypted_data

        # Legacy support: if it's not starting with our prefix, we assume it's plaintext
        # This allows seamless migration for existing dbs
        if not encrypted_data.startswith(self.PREFIX):
            if self.strict_mode:
                raise DecryptionPolicyError(
                    "Strict crypto mode active: data lacks encryption prefix in strict mode"
                )
            return encrypted_data

        if not self.is_active:
            raise RuntimeError("Database contains encrypted data but no Master Key is loaded.")

        try:
            raw_b64 = encrypted_data[len(self.PREFIX) :]
            combined = base64.b64decode(raw_b64)
            nonce = combined[:_NONCE_LENGTH]
            ciphertext = combined[_NONCE_LENGTH:]

            key = self._get_tenant_key(tenant_id)
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except (InvalidKey, InvalidTag) as e:
            raise ValueError(
                f"Decryption failed for tenant '{tenant_id}'. Possible cross-tenant access attempt or corrupted data."
            ) from e
        except (ValueError, TypeError, binascii.Error) as e:
            raise ValueError(f"AES-GCM Decryption Failed (Data tampered?): {e}") from e

    def encrypt_json(self, data: dict[str, Any] | None, tenant_id: str = "default") -> str | None:
        """Encrypts a JSON dictionary."""
        if not data:
            return None
        return self.encrypt_str(json.dumps(data), tenant_id=tenant_id)

    def decrypt_json(
        self, encrypted_data: str | None, tenant_id: str = "default"
    ) -> dict[str, Any] | None:
        """Decrypts back into a JSON dictionary."""
        plain = self.decrypt_str(encrypted_data, tenant_id=tenant_id)
        if not plain:
            return None
        try:
            from typing import cast
            return cast(dict[str, Any], json.loads(plain))
        except json.JSONDecodeError:
            logger.warning("decrypt_json: invalid JSON after decryption, returning empty dict")
            return {}


_default_encrypter_instance = None
_encrypter_lock = threading.Lock()


def get_default_encrypter() -> CortexEncrypter:
    """Returns a lazily-initialized singleton encrypter instance (thread-safe)."""
    global _default_encrypter_instance
    if _default_encrypter_instance is None:
        with _encrypter_lock:
            if _default_encrypter_instance is None:
                from cortex.crypto.keyring import get_master_key

                _default_encrypter_instance = CortexEncrypter(get_master_key())
    return _default_encrypter_instance


def reset_default_encrypter() -> None:
    """Resets the singleton encrypter instance.
    Useful for testing or when the Master Key environment changes.
    """
    global _default_encrypter_instance
    _default_encrypter_instance = None

"""
CORTEX v6 — AES-256-GCM Envelope Encryption.
Application-level encryption for L3 Ledgers.
"""

import base64
import json
import os
from typing import Any

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class CortexEncrypter:
    """Zero-Knowledge Data Encrypter for DB rows.
    Uses AES-GCM (Authenticated Encryption).
    """

    PREFIX = "v6_aesgcm:"

    def __init__(self, master_key: bytes | None):
        if master_key is not None and len(master_key) != 32:
            raise ValueError("AES-256 requires a 32-byte master key.")
        self._master_key = master_key
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
            length=32,
            salt=b"cortex_v6_tenant_isolation_salt",
            info=tenant_id.encode("utf-8"),
        )
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
            raise RuntimeError("Cannot encrypt without a Master Key.")

        key = self._get_tenant_key(tenant_id)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
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
            return encrypted_data

        if not self.is_active:
            raise RuntimeError("Database contains encrypted data but no Master Key is loaded.")

        try:
            raw_b64 = encrypted_data[len(self.PREFIX) :]
            combined = base64.b64decode(raw_b64)
            nonce = combined[:12]
            ciphertext = combined[12:]

            key = self._get_tenant_key(tenant_id)
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except InvalidKey as e:
            raise ValueError(
                f"Decryption failed for tenant '{tenant_id}'. "
                "Possible cross-tenant access attempt."
            ) from e
        except Exception as e:
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
            return json.loads(plain)
        except json.JSONDecodeError:
            return {}


_default_encrypter_instance = None


def get_default_encrypter() -> CortexEncrypter:
    """Returns a lazily-initialized singleton encrypter instance."""
    global _default_encrypter_instance
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

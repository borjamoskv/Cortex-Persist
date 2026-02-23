"""
CORTEX v6 — AES-256-GCM Envelope Encryption.
Application-level encryption for L3 Ledgers.
"""

import base64
import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CortexEncrypter:
    """Zero-Knowledge Data Encrypter for DB rows.
    Uses AES-GCM (Authenticated Encryption).
    """

    PREFIX = "v6_aesgcm:"

    def __init__(self, key: bytes | None):
        if key is not None and len(key) != 32:
            raise ValueError("AES-256 requires a 32-byte key.")
        self._key = key

    @property
    def is_active(self) -> bool:
        return self._key is not None

    def encrypt_str(self, data: str | None) -> str | None:
        """Encrypt a string and return a safe Base64 representation.
        If data is None or empty, return as is.
        """
        if not data:
            return data
        if not self.is_active:
            raise RuntimeError("Cannot encrypt without a Master Key.")

        aesgcm = AESGCM(self._key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data.encode("utf-8"), None)

        # We prepend a clear v6 prefix so we can detect it on decrypt
        combined = nonce + ciphertext
        return self.PREFIX + base64.b64encode(combined).decode("utf-8")

    def decrypt_str(self, encrypted_data: str | None) -> str | None:
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

            aesgcm = AESGCM(self._key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except Exception as e:
            raise ValueError(f"AES-GCM Decryption Failed (Data tampered?): {e}") from e

    def encrypt_json(self, data: dict[str, Any] | None) -> str | None:
        """Encrypts a JSON dictionary."""
        if not data:
            return None
        return self.encrypt_str(json.dumps(data))

    def decrypt_json(self, encrypted_data: str | None) -> dict[str, Any] | None:
        """Decrypts back into a JSON dictionary."""
        plain = self.decrypt_str(encrypted_data)
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

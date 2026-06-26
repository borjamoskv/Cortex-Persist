# [C5-REAL] Exergy-Maximized
"""Cryptographic Vaults.

Implements L3 Application-Level Encryption using AES-GCM.
"""

from __future__ import annotations

import base64
import os

__all__ = ["Vault"]

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    _HAS_AESGCM = True
except ImportError:
    _HAS_AESGCM = False
    AESGCM = None  # type: ignore


class Vault:
    """Secure Vault for storing sensitive facts."""

    _key: bytes | None

    def __init__(self, key: bytes | None = None) -> None:
        if not _HAS_AESGCM:
            self._key = None
            return

        if key:
            self._key = key
            return

        # Load from env or generate
        env_key = os.environ.get("CORTEX_VAULT_KEY")
        if not env_key:
            # For dev/testing, allow no key (disabled encryption)
            self._key = None
            return

        try:
            self._key = base64.b64decode(env_key)
        except (OSError, ValueError):
            # Invalid key is fatal.
            self._key = None

    @property
    def is_available(self) -> bool:
        return AESGCM is not None and self._key is not None

    def encrypt(self, data: str) -> str:
        """Encrypt string using AES-GCM."""
        if not self.is_available:
            raise RuntimeError("Encryption not available (missing key or library)")

        assert self._key is not None
        aesgcm = AESGCM(self._key)  # type: ignore
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data.encode("utf-8"), None)

        # Format: base64(nonce + ciphertext)
        return base64.b64encode(nonce + ciphertext).decode("utf-8")

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string using AES-GCM."""
        if not self.is_available:
            raise RuntimeError("Encryption not available (missing key or library)")

        try:
            raw = base64.b64decode(encrypted_data)
            nonce = raw[:12]
            ciphertext = raw[12:]

            assert self._key is not None
            aesgcm = AESGCM(self._key)  # type: ignore
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except (OSError, ValueError) as e:
            raise ValueError(f"Decryption failed: {e}") from e

    @staticmethod
    def generate_key() -> str:
        """Generate a new secure key (base64 encoded)."""
        if not _HAS_AESGCM:
            raise ImportError("cryptography library not installed")
        key = AESGCM.generate_key(bit_length=256)  # type: ignore
        return base64.b64encode(key).decode("utf-8")

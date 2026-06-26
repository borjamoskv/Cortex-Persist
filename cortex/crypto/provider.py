# [C5-REAL] Exergy-Maximized
"""
Cryptographic Provider Architecture.
Decouples and centralizes hashing, signatures, key derivation, and randomness
into distinct providers for FIPS-readiness, auditing, and dependency injection.
"""

import hashlib
import hmac
import os


class HashProvider:
    """Provides cryptographic hashing algorithms."""

    @staticmethod
    def sha256(data: bytes | str) -> str:
        """Returns hex digest of SHA-256 hash."""
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def sha512(data: bytes | str) -> str:
        """Returns hex digest of SHA-512 hash."""
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha512(data).hexdigest()


class SignatureProvider:
    """Provides asymmetric and symmetric signing capabilities."""

    @staticmethod
    def sign_hmac_sha256(key: bytes | str, data: bytes | str) -> str:
        """Returns hex digest HMAC-SHA256 signature."""
        if isinstance(key, str):
            key = key.encode("utf-8")
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hmac.new(key, data, hashlib.sha256).hexdigest()

    @staticmethod
    def verify_hmac_sha256(key: bytes | str, data: bytes | str, signature: str) -> bool:
        """Constant-time verification of HMAC-SHA256 signature."""
        expected = SignatureProvider.sign_hmac_sha256(key, data)
        return hmac.compare_digest(expected, signature)


class KDFProvider:
    """Provides Key Derivation Functions (KDF)."""

    @staticmethod
    def pbkdf2_hmac_sha256(secret: bytes | str, salt: bytes, iterations: int = 100000) -> bytes:
        """Derives a cryptographic key using PBKDF2 with HMAC-SHA256."""
        if isinstance(secret, str):
            secret = secret.encode("utf-8")
        return hashlib.pbkdf2_hmac("sha256", secret, salt, iterations)


class RandomProvider:
    """Provides secure pseudo-random entropy."""

    @staticmethod
    def generate_bytes(num_bytes: int = 32) -> bytes:
        """Returns secure random bytes."""
        return os.urandom(num_bytes)

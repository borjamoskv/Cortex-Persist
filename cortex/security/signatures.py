"""
CORTEX v8 — Ed25519 Digital Signatures.

Provides cryptographic fact signing and verification.
Every fact stored in the ledger can carry a digital signature from
the agent/user that created it, proving provenance beyond hash chains.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

__all__ = [
    "Ed25519Signer",
    "SignatureVerificationError",
    "generate_keypair",
    "get_default_signer",
]

logger = logging.getLogger("cortex.security.signatures")

_KEYRING_SERVICE = "cortex_v6"
_KEYRING_PRIVKEY = "ed25519_private_key"
_KEYRING_PUBKEY = "ed25519_public_key"


class SignatureVerificationError(Exception):
    """Raised when a signature fails verification."""


def generate_keypair() -> tuple[bytes, bytes]:
    """Generate a new Ed25519 keypair.

    Returns:
        Tuple of (private_key_bytes, public_key_bytes) in raw format.
    """
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return private_bytes, public_bytes


def _canonical_payload(content: str, fact_hash: str) -> bytes:
    """Create a canonical byte payload for signing.

    Combines content hash with the fact hash to ensure
    both the content and its position in the chain are signed.
    """
    content_digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    canonical = f"{content_digest}:{fact_hash}"
    return canonical.encode("utf-8")


class Ed25519Signer:
    """Ed25519 digital signature engine for CORTEX facts.

    Provides sign/verify operations using Ed25519 keys.
    Keys can be loaded from raw bytes or from the OS keyring.
    """

    def __init__(
        self,
        private_key_bytes: bytes | None = None,
        public_key_bytes: bytes | None = None,
    ) -> None:
        self._private_key: Ed25519PrivateKey | None = None
        self._public_key: Ed25519PublicKey | None = None

        if private_key_bytes:
            self._private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
            self._public_key = self._private_key.public_key()
        elif public_key_bytes:
            self._public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)

    @property
    def can_sign(self) -> bool:
        """Whether this signer has a private key and can create signatures."""
        return self._private_key is not None

    @property
    def can_verify(self) -> bool:
        """Whether this signer has a public key and can verify signatures."""
        return self._public_key is not None

    @property
    def public_key_b64(self) -> str | None:
        """Base64-encoded public key, or None if no key loaded."""
        if self._public_key is None:
            return None
        raw = self._public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
        return base64.b64encode(raw).decode("ascii")

    def sign(self, content: str, fact_hash: str) -> str:
        """Sign a fact's content + hash, returning base64-encoded signature.

        Args:
            content: The plaintext fact content.
            fact_hash: The SHA-256 hash of the fact (from the ledger).

        Returns:
            Base64-encoded Ed25519 signature.

        Raises:
            RuntimeError: If no private key is loaded.
        """
        if self._private_key is None:
            raise RuntimeError("No private key loaded — cannot sign")

        payload = _canonical_payload(content, fact_hash)
        raw_sig = self._private_key.sign(payload)
        return base64.b64encode(raw_sig).decode("ascii")

    def verify(
        self,
        content: str,
        fact_hash: str,
        signature_b64: str,
        public_key_b64: str | None = None,
    ) -> bool:
        """Verify a fact's signature.

        Args:
            content: The plaintext fact content.
            fact_hash: The SHA-256 hash of the fact.
            signature_b64: Base64-encoded signature to verify.
            public_key_b64: Optional external public key (overrides instance key).

        Returns:
            True if signature is valid.

        Raises:
            SignatureVerificationError: If signature is invalid.
        """
        pub_key = self._resolve_public_key(public_key_b64)
        payload = _canonical_payload(content, fact_hash)
        raw_sig = base64.b64decode(signature_b64)

        try:
            pub_key.verify(raw_sig, payload)
            return True
        except InvalidSignature as exc:
            raise SignatureVerificationError("Ed25519 signature verification failed") from exc

    def _resolve_public_key(self, public_key_b64: str | None) -> Ed25519PublicKey:
        """Resolve which public key to use for verification."""
        if public_key_b64:
            raw = base64.b64decode(public_key_b64)
            return Ed25519PublicKey.from_public_bytes(raw)
        if self._public_key:
            return self._public_key
        raise RuntimeError("No public key available for verification")

    def to_dict(self) -> dict[str, Any]:
        """Serialize signer metadata (public key only, never private)."""
        return {
            "algorithm": "Ed25519",
            "public_key": self.public_key_b64,
            "can_sign": self.can_sign,
        }


# Module-level singleton
_default_signer: Ed25519Signer | None = None


def get_default_signer() -> Ed25519Signer | None:
    """Get the default signer, loading from keyring if available.

    Returns None if no signing key is configured — signing is optional.
    Falls back to CORTEX_ED25519_PRIVATE_KEY env var for CI environments.
    """
    global _default_signer
    if _default_signer is not None:
        return _default_signer

    priv_b64: str | None = None

    # Try OS keyring first (skip in testing)
    if not os.environ.get("CORTEX_TESTING"):
        try:
            import keyring

            priv_b64 = keyring.get_password(_KEYRING_SERVICE, _KEYRING_PRIVKEY)
        except (ImportError, OSError, ValueError) as exc:
            logger.debug("Keyring Ed25519 key not available: %s", exc)

    # Env var fallback for CI/CD
    if not priv_b64:
        priv_b64 = os.environ.get("CORTEX_ED25519_PRIVATE_KEY")

    if priv_b64:
        try:
            priv_bytes = base64.b64decode(priv_b64)
            _default_signer = Ed25519Signer(private_key_bytes=priv_bytes)
            logger.info("Ed25519 signer loaded")
            return _default_signer
        except (ValueError, Exception) as exc:
            logger.warning("Failed to load Ed25519 key: %s", exc)

    return None


def configure_signer(private_key_bytes: bytes) -> Ed25519Signer:
    """Configure and persist a signing key.

    Stores the private key in the OS keyring and sets the module singleton.
    """
    global _default_signer
    signer = Ed25519Signer(private_key_bytes=private_key_bytes)
    _default_signer = signer

    try:
        import keyring

        priv_b64 = base64.b64encode(private_key_bytes).decode("ascii")
        keyring.set_password(_KEYRING_SERVICE, _KEYRING_PRIVKEY, priv_b64)

        pub_b64 = signer.public_key_b64
        if pub_b64:
            keyring.set_password(_KEYRING_SERVICE, _KEYRING_PUBKEY, pub_b64)
        logger.info("Ed25519 keypair stored in OS keyring")
    except (ImportError, OSError, ValueError) as exc:
        logger.warning("Could not persist key to keyring: %s", exc)

    return signer

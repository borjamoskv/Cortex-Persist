# [C5-REAL] Exergy-Maximized
"""
Substrate for CORTEX Agent Cryptographic Identity.

Exposes Ed25519 primitives for subagents to generate robust execution proofs
(Zero-Knowledge signatures) over their stochastically derived states before
submitting them to the Sovereign Ledger.
"""

import base64
import hashlib
from typing import NamedTuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519


class AgentKeyPair(NamedTuple):
    """The local identity of an autonomous agent."""

    public_key_b64: str
    private_key_b64: str


class ZKSwarmIdentity:
    """Manages cryptographic signing and verification for the CORTEX ZK-Swarm."""

    @staticmethod
    def generate_keypair() -> AgentKeyPair:
        """Generates a fresh Ed25519 keypair for an agent session.

        Returns:
            AgentKeyPair containing the base64-encoded representations.
        """
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # Serialize to raw bytes and base64 encode for transport efficiency
        priv_bytes = private_key.private_bytes_raw()
        pub_bytes = public_key.public_bytes_raw()

        return AgentKeyPair(
            public_key_b64=base64.b64encode(pub_bytes).decode("utf-8"),
            private_key_b64=base64.b64encode(priv_bytes).decode("utf-8"),
        )

    @staticmethod
    def sign_payload(content: str, private_key_b64: str) -> str:
        """Deterministic signature over the state content delta.

        Args:
            content: The raw text/JSON proposed by the agent.
            private_key_b64: The base64 Ed25519 private key.

        Returns:
            A base64-encoded signature serving as the 'ZK-proof' of generating authority.
        """
        priv_bytes = base64.b64decode(private_key_b64)
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)

        # We sign the SHA-256 hash of the content to enforce thermodynamic consistency
        content_hash = hashlib.sha256(content.encode("utf-8")).digest()
        signature_bytes = private_key.sign(content_hash)

        return base64.b64encode(signature_bytes).decode("utf-8")

    @staticmethod
    def verify_payload(content: str, public_key_b64: str, signature_b64: str) -> bool:
        """Verifies an incoming agent signature against the raw payload.

        Args:
            content: The raw text/JSON actually received at the gateway.
            public_key_b64: The declared public key of the agent.
            signature_b64: The proof boundary carrying the signature.

        Returns:
            True if mathematically valid, False otherwise.
        """
        try:
            pub_bytes = base64.b64decode(public_key_b64)
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)

            signature_bytes = base64.b64decode(signature_b64)
            content_hash = hashlib.sha256(content.encode("utf-8")).digest()

            public_key.verify(signature_bytes, content_hash)
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False

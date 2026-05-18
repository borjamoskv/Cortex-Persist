"""
Substrate for CORTEX Agent Cryptographic Identity.

Exposes Ed25519 primitives for subagents to generate robust execution proofs
(Zero-Knowledge signatures) over their stochastically derived states before
submitting them to the Sovereign Ledger.
"""

import base64
import hashlib
from typing import NamedTuple

import cortex_core


class AgentKeyPair(NamedTuple):
    """The local identity of an autonomous agent."""

    public_key_b64: str
    private_key_b64: str


class ZKSwarmIdentity:
    """Manages cryptographic signing and verification for the CORTEX ZK-Swarm."""

    @staticmethod
    def generate_keypair() -> AgentKeyPair:
        """Generates a fresh Ed25519 keypair for an agent session."""
        pub, priv = cortex_core.ZKSwarmIdentity.generate_keypair()
        return AgentKeyPair(
            public_key_b64=pub,
            private_key_b64=priv,
        )

    @staticmethod
    def sign_payload(content: str, private_key_b64: str) -> str:
        """Deterministic signature over the state content delta."""
        return cortex_core.ZKSwarmIdentity.sign_payload(content, private_key_b64)

    @staticmethod
    def verify_payload(content: str, public_key_b64: str, signature_b64: str) -> bool:
        """Verifies an incoming agent signature against the raw payload."""
        return cortex_core.ZKSwarmIdentity.verify_payload(content, public_key_b64, signature_b64)

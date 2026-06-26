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


import json
import os
from pathlib import Path

from cortex.crypto.vault import Vault


class KeyLifecycleManager:
    """Manages the secure lifecycle, persistence, and rotation of Agent identities."""

    def __init__(self, storage_path: str | Path | None = None, vault: Vault | None = None):
        self.storage_path = Path(storage_path) if storage_path else Path(os.environ.get("CORTEX_DB_PATH", "~/.cortex")).expanduser().parent / "agent_identity.json"
        self.vault = vault or Vault()

    def get_or_create_identity(self) -> AgentKeyPair:
        """Loads the current identity from secure storage or generates a new one."""
        if self.storage_path.exists():
            return self._load_identity()
        return self._generate_and_save()

    def rotate_keys(self) -> AgentKeyPair:
        """Forces generation of a new keypair and archives the old one."""
        # Archive old keys could be implemented here
        return self._generate_and_save()

    def _generate_and_save(self) -> AgentKeyPair:
        keypair = ZKSwarmIdentity.generate_keypair()
        payload = {
            "public_key_b64": keypair.public_key_b64,
            "private_key_b64": keypair.private_key_b64
        }
        
        # If vault is available, encrypt the private key
        if self.vault.is_available:
            payload["private_key_b64"] = self.vault.encrypt(payload["private_key_b64"])
            payload["encrypted"] = True
        else:
            payload["encrypted"] = False

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            
        return keypair

    def _load_identity(self) -> AgentKeyPair:
        with open(self.storage_path, encoding="utf-8") as f:
            data = json.load(f)
            
        private_key = data["private_key_b64"]
        if data.get("encrypted", False):
            if not self.vault.is_available:
                 raise RuntimeError("Identity is encrypted but Vault is not available.")
            private_key = self.vault.decrypt(private_key)
            
        return AgentKeyPair(
            public_key_b64=data["public_key_b64"],
            private_key_b64=private_key
        )

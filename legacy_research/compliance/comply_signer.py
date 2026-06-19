# [C5-REAL] Exergy-Maximized
"""ComplySigner - Cryptographic Ed25519 identities for agent provenance."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

logger = logging.getLogger("cortex.compliance.comply_signer")

DEFAULT_KEYS_DIR = Path("~/.cortex/keys").expanduser()


class ComplySigner:
    """Manages Ed25519 keys and signs/verifies agent decisions to establish provenance."""

    def __init__(self, keys_dir: str | Path = DEFAULT_KEYS_DIR) -> None:
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(parents=True, exist_ok=True)

    def _get_key_paths(self, agent_id: str) -> tuple[Path, Path]:
        # Sanitize agent name to prevent path traversal
        safe_id = agent_id.replace(":", "_").replace("/", "_").replace("\\", "_")
        return self.keys_dir / f"{safe_id}_private.pem", self.keys_dir / f"{safe_id}_public.pem"

    def get_or_create_agent_keys(self, agent_id: str) -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """Load existing Ed25519 keys for the agent or generate a new pair."""
        priv_path, pub_path = self._get_key_paths(agent_id)

        if priv_path.exists() and pub_path.exists():
            try:
                with open(priv_path, "rb") as f:
                    private_key = serialization.load_pem_private_key(f.read(), password=None)
                with open(pub_path, "rb") as f:
                    public_key = serialization.load_pem_public_key(f.read())
                if isinstance(private_key, ed25519.Ed25519PrivateKey) and isinstance(public_key, ed25519.Ed25519PublicKey):
                    return private_key, public_key
            except Exception as e:
                logger.error(f"Failed to load keys for agent {agent_id}: {e}. Regenerating.")

        # Generate new pair
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # Serialize & write private key
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        with open(priv_path, "wb") as f:
            f.write(private_bytes)
        # Restrict permissions
        priv_path.chmod(0o600)

        # Serialize & write public key
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        with open(pub_path, "wb") as f:
            f.write(public_bytes)

        return private_key, public_key

    def sign_payload(self, agent_id: str, payload: dict[str, Any] | str) -> str:
        """Sign a payload using the agent's private key. Returns signature as a base64 string.

        The payload is canonicalized using deterministic JSON serialization.
        """
        private_key, _ = self.get_or_create_agent_keys(agent_id)

        if isinstance(payload, dict):
            # Deterministic serialization: sorted keys, no whitespace
            serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        else:
            serialized = payload.encode("utf-8")

        signature = private_key.sign(serialized)
        return base64.b64encode(signature).decode("utf-8")

    def verify_payload(self, agent_id: str, payload: dict[str, Any] | str, signature_b64: str) -> bool:
        """Verify the payload signature using the agent's public key."""
        try:
            _, public_key = self.get_or_create_agent_keys(agent_id)

            if isinstance(payload, dict):
                serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            else:
                serialized = payload.encode("utf-8")

            signature = base64.b64decode(signature_b64)
            public_key.verify(signature, serialized)
            return True
        except Exception as e:
            logger.debug(f"Signature verification failed for agent {agent_id}: {e}")
            return False

    def export_public_key_hex(self, agent_id: str) -> str:
        """Export the raw public key bytes in hex representation."""
        _, public_key = self.get_or_create_agent_keys(agent_id)
        # Get raw 32-byte public key representation for Ed25519
        raw_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return raw_bytes.hex()

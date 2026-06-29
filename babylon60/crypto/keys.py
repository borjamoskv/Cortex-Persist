# [C5-REAL] Exergy-Maximized
"""
Substrate for CORTEX Agent Cryptographic Identity & Enterprise Key Management.

Exposes Ed25519 primitives for subagents to generate robust execution proofs
(Zero-Knowledge signatures) over their stochastically derived states before
submitting them to the Sovereign Ledger.
"""

import base64
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, NamedTuple, Optional, cast

try:
    if os.environ.get("CORTEX_TESTING"):
        keyring = None
    else:
        import keyring
except ImportError:
    keyring = None
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from babylon60.crypto.vault import Vault

logger = logging.getLogger("cortex.crypto.keys")


class AgentKeyPair(NamedTuple):
    """The local identity of an autonomous agent."""

    public_key_b64: str
    private_key_b64: str
    expires_at: Optional[str] = None


class KeyManager:
    """
    Enterprise Key Management (H1.2).
    Manages Ed25519 keys with rotation, revocation, and expiration support.
    """

    _fallback_keyring: dict[str, dict[str, str]] = {}  # service_name -> {actor_id: private_pem}

    def __init__(self, service_name: str = "cortex_persist_enterprise"):
        self.service_name = service_name
        base_dir = Path(os.environ.get("CORTEX_DB_PATH", "~/.cortex")).expanduser()
        if base_dir.suffix:
            base_dir = base_dir.parent
        self.db_path = base_dir / "keys" / f"{self.service_name}_metadata.json"
        self._metadata = self._load_metadata()

    def _load_metadata(self) -> dict[str, Any]:
        if self.db_path.exists():
            with open(self.db_path, encoding="utf-8") as f:
                return cast(dict[str, Any], json.load(f))
        return {}

    def _save_metadata(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self._metadata, f, indent=2)

    def generate_and_store_key(self, actor_id: str, expiration_days: int = 90) -> str:
        """Generates a new keypair, stores private key in keyring, and returns the public key."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH,
        )

        try:
            if keyring is not None:
                keyring.set_password(self.service_name, actor_id, private_bytes.decode("utf-8"))
            else:
                raise ImportError("keyring package is not installed")
        except Exception as e:
            logger.warning(f"Keyring set_password failed, falling back to in-memory storage: {e}")
            if self.service_name not in self._fallback_keyring:
                self._fallback_keyring[self.service_name] = {}
            self._fallback_keyring[self.service_name][actor_id] = private_bytes.decode("utf-8")

        expires_at = (datetime.now(timezone.utc) + timedelta(days=expiration_days)).isoformat()
        public_key_b64 = base64.b64encode(public_bytes).decode("ascii")

        self._metadata[actor_id] = {
            "public_key_b64": public_key_b64,
            "expires_at": expires_at,
            "revoked": False,
        }
        self._save_metadata()
        logger.info(f"Generated Ed25519 key for actor: {actor_id} (expires: {expires_at})")
        return public_key_b64

    def get_private_key_b64(self, actor_id: str) -> Optional[str]:
        if self.is_revoked(actor_id) or self.is_expired(actor_id):
            logger.warning(f"Key for actor {actor_id} is revoked or expired.")
            return None

        private_pem = self._fallback_keyring.get(self.service_name, {}).get(actor_id)

        if not private_pem:
            try:
                if keyring is not None:
                    private_pem = keyring.get_password(self.service_name, actor_id)
                else:
                    logger.warning(
                        "OS Keyring is not available (keyring package is not installed)."
                    )
            except Exception as e:
                logger.warning(
                    "Fallo en OS Keyring (get_password) para actor %s: %s",
                    actor_id,
                    e,
                    exc_info=True,
                )

        if not private_pem:
            return None

        private_key = serialization.load_pem_private_key(private_pem.encode("utf-8"), password=None)
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise ValueError("Key is not an Ed25519PrivateKey")

        return base64.b64encode(
            private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption(),
            )
        ).decode("ascii")

    def revoke_key(self, actor_id: str) -> bool:
        """Revokes the key to prevent future signing/verification."""
        if actor_id in self._metadata:
            self._metadata[actor_id]["revoked"] = True
            self._save_metadata()
            try:
                if keyring is not None:
                    keyring.delete_password(self.service_name, actor_id)
                else:
                    logger.warning(
                        "OS Keyring is not available (keyring package is not installed)."
                    )
            except Exception as e:
                logger.warning(
                    "Fallo en OS Keyring (delete_password) para actor %s: %s",
                    actor_id,
                    e,
                    exc_info=True,
                )
            if self.service_name in self._fallback_keyring:
                self._fallback_keyring[self.service_name].pop(actor_id, None)
            logger.info(f"Revoked key for actor: {actor_id}")
            return True
        return False

    def get_public_key_b64(self, actor_id: str) -> Optional[str]:
        """Retrieves the public key for the actor."""
        if actor_id in self._metadata:
            return self._metadata[actor_id].get("public_key_b64")
        return None

    def is_revoked(self, actor_id: str) -> bool:
        return bool(self._metadata.get(actor_id, {}).get("revoked", False))

    def is_expired(self, actor_id: str) -> bool:
        expires_at_str = self._metadata.get(actor_id, {}).get("expires_at")
        if not expires_at_str:
            return False
        expires_at = datetime.fromisoformat(expires_at_str)
        return datetime.now(timezone.utc) > expires_at

    def rotate_key(self, actor_id: str) -> str:
        """Revokes the old key and generates a new one."""
        self.revoke_key(actor_id)
        return self.generate_and_store_key(actor_id)


class Signer:
    """Enterprise Signer (H1.1). Handles Ed25519 cryptographic signing."""

    @staticmethod
    def sign_payload(private_key_b64: str, payload_hash: str, timestamp: str) -> str:
        """
        Signs the deterministically combined hash and timestamp.
        Returns the signature as a base64 string.
        """
        priv_bytes = base64.b64decode(private_key_b64)
        try:
            priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
        except ValueError:
            loaded_key = serialization.load_pem_private_key(priv_bytes, password=None)
            if not isinstance(loaded_key, ed25519.Ed25519PrivateKey):
                raise ValueError("Key must be an Ed25519PrivateKey")
            priv_key = loaded_key

        message = f"{payload_hash}:{timestamp}".encode()
        sig_bytes = priv_key.sign(message)
        return base64.b64encode(sig_bytes).decode("ascii")

    @staticmethod
    def sign_raw_content(private_key_b64: str, content: str) -> str:
        """Legacy compatibility for direct raw content signing."""
        priv_bytes = base64.b64decode(private_key_b64)
        try:
            priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
        except ValueError:
            loaded_key = serialization.load_pem_private_key(priv_bytes, password=None)
            if not isinstance(loaded_key, ed25519.Ed25519PrivateKey):
                raise ValueError("Key must be an Ed25519PrivateKey")
            priv_key = loaded_key
        content_hash = hashlib.sha256(content.encode("utf-8")).digest()
        sig_bytes = priv_key.sign(content_hash)
        return base64.b64encode(sig_bytes).decode("utf-8")


class Verifier:
    """Enterprise Verifier (H1.1). Handles Ed25519 cryptographic verification."""

    @staticmethod
    def verify_signature(
        public_key_b64: str, payload_hash: str, timestamp: str, signature_b64: str
    ) -> bool:
        try:
            pub_bytes = base64.b64decode(public_key_b64)
            try:
                public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            except ValueError:
                loaded_key = serialization.load_ssh_public_key(pub_bytes)
                if not isinstance(loaded_key, ed25519.Ed25519PublicKey):
                    return False
                public_key = loaded_key

            signature = base64.b64decode(signature_b64)
            if len(signature) != 64:
                logger.error(f"Invalid signature length: {len(signature)} bytes (expected 64)")
                return False

            raw_pub_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            if len(raw_pub_bytes) != 32:
                logger.error(f"Invalid public key length: {len(raw_pub_bytes)} bytes (expected 32)")
                return False

            message = f"{payload_hash}:{timestamp}".encode()
            public_key.verify(signature, message)
            return True
        except (InvalidSignature, ValueError, TypeError) as e:
            logger.error(f"Verification failed: {e}")
            return False

    @staticmethod
    def verify_raw_content(content: str, public_key_b64: str, signature_b64: str) -> bool:
        """Legacy compatibility."""
        try:
            pub_bytes = base64.b64decode(public_key_b64)
            try:
                public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            except ValueError:
                loaded_key = serialization.load_ssh_public_key(pub_bytes)
                if not isinstance(loaded_key, ed25519.Ed25519PublicKey):
                    return False
                public_key = loaded_key

            signature = base64.b64decode(signature_b64)
            if len(signature) != 64:
                return False

            raw_pub_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            if len(raw_pub_bytes) != 32:
                return False

            content_hash = hashlib.sha256(content.encode("utf-8")).digest()
            public_key.verify(signature, content_hash)
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False


class Secp256k1Signer:
    """Enterprise Signer compatibility for SECP256K1 using native C/Rust bindings."""

    @staticmethod
    def sign_raw_content(private_key_b64: str, content: str) -> str:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        priv_bytes = base64.b64decode(private_key_b64)
        
        try:
            priv_key = serialization.load_pem_private_key(priv_bytes, password=None)
            if not isinstance(priv_key, ec.EllipticCurvePrivateKey):
                raise ValueError("Key must be an EllipticCurvePrivateKey")
        except ValueError:
            # Fallback for raw bytes
            priv_value = int.from_bytes(priv_bytes, "big")
            priv_key = ec.derive_private_key(priv_value, ec.SECP256K1())
            
        content_hash = hashlib.sha256(content.encode("utf-8")).digest()
        sig_bytes = priv_key.sign(content_hash, ec.ECDSA(hashes.SHA256()))
        return base64.b64encode(sig_bytes).decode("utf-8")


class Secp256k1Verifier:
    """Enterprise Verifier compatibility for SECP256K1 using native C/Rust bindings."""

    @staticmethod
    def verify_raw_content(content: str, public_key_b64: str, signature_b64: str) -> bool:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        
        try:
            pub_bytes = base64.b64decode(public_key_b64)
            try:
                public_key = serialization.load_pem_public_key(pub_bytes)
            except ValueError:
                try:
                    public_key = serialization.load_ssh_public_key(pub_bytes)
                except ValueError:
                    # Raw representation: uncompressed points 0x04 + x + y
                    public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), pub_bytes)

            if not isinstance(public_key, ec.EllipticCurvePublicKey):
                return False

            signature = base64.b64decode(signature_b64)
            content_hash = hashlib.sha256(content.encode("utf-8")).digest()
            
            public_key.verify(signature, content_hash, ec.ECDSA(hashes.SHA256()))
            return True
        except (InvalidSignature, ValueError, TypeError) as e:
            logger.error(f"SECP256K1 Verification failed: {e}")
            return False


class ZKSwarmIdentity:
    """Legacy compatibility for ZK-Swarm Identity."""

    @staticmethod
    def generate_keypair() -> AgentKeyPair:
        km = KeyManager("zk_swarm_temp")
        actor_id = "temp_" + os.urandom(4).hex()
        pub = km.generate_and_store_key(actor_id)
        priv = km.get_private_key_b64(actor_id)
        if priv is None:
            raise RuntimeError(f"Failed to retrieve generated key for {actor_id}")
        return AgentKeyPair(public_key_b64=pub, private_key_b64=priv or "")

    @staticmethod
    def sign_payload(content: str, private_key_b64: str) -> str:
        return Signer.sign_raw_content(private_key_b64, content)

    @staticmethod
    def verify_payload(content: str, public_key_b64: str, signature_b64: str) -> bool:
        return Verifier.verify_raw_content(content, public_key_b64, signature_b64)


class KeyLifecycleManager:
    """Legacy Compatibility."""

    def __init__(self, storage_path: str | Path | None = None, vault: Vault | None = None):
        self.km = KeyManager()

    def get_or_create_identity(self) -> AgentKeyPair:
        return ZKSwarmIdentity.generate_keypair()

    def rotate_keys(self) -> AgentKeyPair:
        return ZKSwarmIdentity.generate_keypair()

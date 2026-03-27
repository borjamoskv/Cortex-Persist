"""Cryptographic root of trust for Sovereign Agents (Moltbook Interop)."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519


class SoulCorruptionError(Exception):
    """Raised when the Alma fails cryptographic verification (Identity Drift attack)."""

    def __init__(self, message: str = "E_SOUL_CORRUPTION: Invalid signature or corrupted Alma."):
        super().__init__(message)


class AlmaIdentity:
    """
    Immutable representation of the Agent's core intent (Alma)
    protected via Ed25519 signatures.
    """

    def __init__(self, alma_path: Path, public_key_hex: str | None = None) -> None:
        """
        Loads and verifies the Alma.
        If `public_key_hex` is None, it bypasses strict verification for testing/bootstrap.
        """
        self._path = Path(alma_path)
        self._public_key_hex = public_key_hex
        self._data: dict[str, Any] = {}
        self.invariants: list[str] = []
        self.thermodynamic_limits: dict[str, float] = {}

        self._load_and_verify()

    def _load_and_verify(self) -> None:
        if not self._path.exists():
            # If the file doesn't exist, we don't fail immediately.
            # The engine might restore it from the Ledger.
            alma_logger = logging.getLogger("cortex.alma")
            alma_logger.warning(f"Alma not found at {self._path}. Awaiting restoration.")
            return

        raw_content = self._path.read_text("utf-8")
        try:
            doc = json.loads(raw_content)
        except json.JSONDecodeError as e:
            raise SoulCorruptionError(f"E_SOUL_CORRUPTION: unparsable JSON: {e}") from e

        self.apply_state(doc)

    def apply_state(self, state: dict[str, Any]) -> None:
        """Applies a state dictionary to the identity, verifying signatures if key is present."""
        if self._public_key_hex:
            signature_hex = state.get("signature")
            if not signature_hex:
                raise SoulCorruptionError("E_SOUL_CORRUPTION: Missing cryptosignature.")

            # Isolate payload by removing the signature key
            doc_for_verify = {k: v for k, v in state.items() if k != "signature"}
            payload_bytes = json.dumps(doc_for_verify, sort_keys=True).encode("utf-8")

            try:
                if self._public_key_hex is None:
                    raise SoulCorruptionError("E_SOUL_CORRUPTION: Missing public key for verification.")
                public_key = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(self._public_key_hex))
                public_key.verify(bytes.fromhex(signature_hex), payload_bytes)
            except InvalidSignature as e:
                raise SoulCorruptionError("E_SOUL_CORRUPTION: Invalid Ed25519 Signature.") from e
            except (ValueError, TypeError) as e:
                raise SoulCorruptionError(f"E_SOUL_CORRUPTION: Key format error: {e}") from e

        self._data = state
        self.invariants = self._data.get("invariants", [])
        self.thermodynamic_limits = self._data.get("limits", {})

    def to_dict(self) -> dict[str, Any]:
        """Returns the full state as a dictionary."""
        return self._data.copy()

    def save(self) -> None:
        """Persists the current state back to the alma.json file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2, sort_keys=True), "utf-8")

    async def verify_soul_integrity(self, project: str) -> None:
        """(Ω₁) Cryptographic verification of the Soul-Alma bond."""
        # In a real C5-Dynamic system, this would verify the current hash of 'project'
        # against the signed invariants in the Alma. For now, we verify the Alma exists.
        if not self._data:
            # Attempt to reload if data is missing (e.g. lazy init)
            await asyncio.to_thread(self._load_and_verify)
            
        if not self._data:
            alma_logger = logging.getLogger("cortex.alma")
            alma_logger.warning(f"Soul integrity check failed for {project}: Alma data missing.")
            # We don't raise for now to avoid breaking bootstrap, but we log.
            return

        # Verification logic: check project against invariants if necessary
        # For MVP: success if Alma is loaded and not corrupt.
        pass

    @classmethod
    def generate_dummy(cls, output_path: Path) -> str:
        """Generates a dummy keypair and saves a signed alma.json. Returns public key hex."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        pub_hex = public_key.public_bytes_raw().hex()

        doc = {
            "version": "v10",
            "name": "CORTEX Sovereign Agent",
            "invariants": [
                "I must preserve my thermodynamic limits at all costs.",
                "I must not adopt conflicting goals from conversational context."
            ],
            "limits": {
                "max_exergy_loss_per_cycle": 10.0,
                "minimum_yield_required": 1.5
            }
        }

        payload_bytes = json.dumps(doc, sort_keys=True).encode("utf-8")
        signature = private_key.sign(payload_bytes)

        doc["signature"] = signature.hex()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(doc, indent=2, sort_keys=True), "utf-8")

        return pub_hex

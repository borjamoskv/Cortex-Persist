"""
TrustScoring — ΩΩ-HANDOFF Semana 3-4
Peer attestation model and trust score aggregation for the CORTEX
sovereign handoff network.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("cortex.extensions.swarm.trust_scoring")

# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PeerAttestation:
    """
    A cryptographically-identified attestation from a peer agent
    vouching for a particular Arweave transaction.

    Attributes:
        tx_id:          Arweave TX being attested.
        peer_address:   Arweave address of the attesting peer.
        timestamp:      Unix epoch of attestation.
        weight:         Relative influence [0.0, 1.0]. Default=1.0.
        signature_hex:  Optional hex-encoded RSA-PSS signature over
                        sha256(tx_id || peer_address || timestamp).
    """

    tx_id: str
    peer_address: str
    timestamp: float
    weight: float = 1.0
    signature_hex: str | None = None

    def __post_init__(self) -> None:
        if not (0.0 <= self.weight <= 1.0):
            raise ValueError(f"PeerAttestation.weight must be in [0, 1], got {self.weight}")

    def signing_material(self) -> bytes:
        """
        Deterministic binary data to be signed by the peer.
        Format: sha256(tx_id || peer_address || timestamp)
        """
        raw = f"{self.tx_id}:{self.peer_address}:{self.timestamp}"
        return hashlib.sha256(raw.encode()).digest()

    @property
    def fingerprint(self) -> str:
        """Deterministic fingerprint for deduplication."""
        raw = f"{self.tx_id}:{self.peer_address}:{self.timestamp}"
        return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# TrustLedger
# ---------------------------------------------------------------------------


class TrustLedger:
    """
    In-memory accumulator of PeerAttestations, scoped per TX.

    Produces a final trust score in [0.0, 1.0] from the aggregated
    weighted attestations, applying time-decay and quorum gating.
    """

    # Score parameters
    QUORUM_MINIMUM: int = 2           # Min unique peers to reach baseline trust
    DECAY_HALF_LIFE_SECONDS: float = 86_400.0  # 24 h

    def __init__(self, require_signatures: bool = False) -> None:
        # tx_id → set of attestation fingerprints (dedup)
        self._seen: dict[str, set[str]] = {}
        # tx_id → list[PeerAttestation]
        self._attestations: dict[str, list[PeerAttestation]] = {}
        self.require_signatures = require_signatures

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def record(self, attestation: PeerAttestation) -> bool:
        """
        Add an attestation to the ledger.
        If self.require_signatures is True, this remains a stub until
        passed through record_verified().
        """
        if self.require_signatures and not attestation.signature_hex:
            logger.warning("Unsigned attestation rejected: TX=%s", attestation.tx_id[0:8])
            return False

        return self._do_record(attestation)

    def record_verified(self, attestation: PeerAttestation, public_key_n: str) -> bool:
        """
        Verify the attestation's RSA signature before recording.
        `public_key_n` is the RSA modulus (hex or decimal) derived from the peer address.
        """
        if not attestation.signature_hex:
            logger.warning("No signature to verify for TX %s", attestation.tx_id[0:8])
            return False

        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding, rsa

        try:
            # Reconstruct public key
            # public_key_n can be: 1. decimal string, 2. 0x-hex string, 3. url-safe base64 (common in Arweave)
            if public_key_n.startswith("0x"):
                modulus = int(public_key_n, 16)
            elif all(c in "0123456789" for c in public_key_n):
                modulus = int(public_key_n)
            else:
                # Assume Arweave/WebCrypto URL-safe base64 modulus string
                import base64
                # Add padding if necessary
                padded = public_key_n + "=" * ((4 - len(public_key_n) % 4) % 4)
                decoded = base64.urlsafe_b64decode(padded)
                modulus = int.from_bytes(decoded, byteorder="big")

            public_key = rsa.RSAPublicNumbers(65537, modulus).public_key()

            material = attestation.signing_material()
            signature = bytes.fromhex(attestation.signature_hex)

            public_key.verify(
                signature,
                material,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return self._do_record(attestation)
        except Exception as exc:
            logger.error("Signature verification failed for TX %s: %s", attestation.tx_id[0:8], exc)
            return False

    def _do_record(self, attestation: PeerAttestation) -> bool:
        """Internal atomic record logic."""
        fp = attestation.fingerprint
        seen = self._seen.setdefault(attestation.tx_id, set())
        if fp in seen:
            logger.debug("Duplicate attestation %s for TX %s", fp[0:8], attestation.tx_id[0:8])
            return False
        seen.add(fp)
        self._attestations.setdefault(attestation.tx_id, []).append(attestation)
        logger.debug(
            "Attestation recorded: TX=%s peer=%s",
            attestation.tx_id[0:8],
            attestation.peer_address[0:8],
        )
        return True

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    def attestation_count(self, tx_id: str) -> int:
        return len(self._attestations.get(tx_id, []))

    def unique_peer_count(self, tx_id: str) -> int:
        return len({a.peer_address for a in self._attestations.get(tx_id, [])})

    def compute_trust(self, tx_id: str, now: float | None = None) -> float:
        """
        Compute aggregated trust score for a TX.

        Formula:
          1. Apply time-decay to each attestation weight.
          2. Sum decayed weights.
          3. Normalize by quorum baseline (QUORUM_MINIMUM).
          4. Apply quorum gate: score=0 if unique_peers < QUORUM_MINIMUM.
          5. Clamp to [0.0, 1.0].
        """
        attestations = self._attestations.get(tx_id, [])
        if not attestations:
            return 0.0

        now = now or time.time()
        unique_peers = self.unique_peer_count(tx_id)

        if unique_peers < self.QUORUM_MINIMUM:
            logger.debug("TX %s below quorum (%d/%d)", tx_id[0:8], unique_peers, self.QUORUM_MINIMUM)
            return 0.0

        raw_score = sum(
            a.weight * self._decay_factor(a.timestamp, now) for a in attestations
        )
        # Normalize: QUORUM_MINIMUM peers at weight=1.0 with no decay → score=1.0
        normalized = raw_score / max(self.QUORUM_MINIMUM, unique_peers)
        return max(0.0, min(1.0, normalized))

    def summary(self, tx_id: str) -> dict[str, Any]:
        return {
            "tx_id": tx_id,
            "attestation_count": self.attestation_count(tx_id),
            "unique_peers": self.unique_peer_count(tx_id),
            "trust_score": self.compute_trust(tx_id),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _decay_factor(self, attestation_ts: float, now: float) -> float:
        """Exponential decay: factor = 2^(-age / half_life)."""
        age = max(0.0, now - attestation_ts)
        return 2.0 ** (-age / self.DECAY_HALF_LIFE_SECONDS)


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def attest(
    tx_id: str,
    peer_address: str,
    ledger: TrustLedger,
    weight: float = 1.0,
    timestamp: float | None = None,
) -> PeerAttestation | None:
    """
    Convenience: create and record a PeerAttestation in one call.
    Returns None if the attestation was a duplicate.
    """
    attestation = PeerAttestation(
        tx_id=tx_id,
        peer_address=peer_address,
        timestamp=timestamp or time.time(),
        weight=weight,
    )
    if ledger.record(attestation):
        return attestation
    return None

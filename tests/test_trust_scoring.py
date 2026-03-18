"""Tests for TrustLedger peer attestation scoring."""

import time

import pytest

from cortex.extensions.swarm.identity import IdentityAnchor
from cortex.extensions.swarm.trust_scoring import (
    PeerAttestation,
    TrustLedger,
    attest,
)

# ------------------------------------------------------------------
# Basic TrustLedger behavior
# ------------------------------------------------------------------


def test_record_and_compute_trust():
    """Quorum gate: 2 unique peers required for non-zero score."""
    ledger = TrustLedger()
    now = time.time()

    # One peer → below quorum → 0.0
    attest("tx_a", "peer_1", ledger, timestamp=now)
    assert ledger.compute_trust("tx_a", now=now) == 0.0

    # Two unique peers → quorum met → positive score
    attest("tx_a", "peer_2", ledger, timestamp=now)
    score = ledger.compute_trust("tx_a", now=now)
    assert score > 0.0
    assert score <= 1.0


def test_duplicate_attestation_rejected():
    """Fingerprint dedup prevents double-counting."""
    ledger = TrustLedger()
    now = time.time()

    att = PeerAttestation(
        tx_id="tx_b",
        peer_address="peer_1",
        timestamp=now,
    )
    assert ledger.record(att) is True
    assert ledger.record(att) is False
    assert ledger.attestation_count("tx_b") == 1


def test_time_decay_reduces_score():
    """Attestations from 48h ago score lower than fresh ones."""
    ledger = TrustLedger()
    past = time.time() - 172_800  # 48h ago
    now = time.time()

    attest("tx_c", "peer_1", ledger, timestamp=past)
    attest("tx_c", "peer_2", ledger, timestamp=past)
    decayed = ledger.compute_trust("tx_c", now=now)

    # Fresh attestations for comparison
    ledger2 = TrustLedger()
    attest("tx_c", "peer_1", ledger2, timestamp=now)
    attest("tx_c", "peer_2", ledger2, timestamp=now)
    fresh = ledger2.compute_trust("tx_c", now=now)

    assert decayed < fresh


# ------------------------------------------------------------------
# Signature verification
# ------------------------------------------------------------------


def test_require_signatures_rejects_unsigned():
    """With require_signatures=True, unsigned attestations are rejected."""
    ledger = TrustLedger(require_signatures=True)
    att = PeerAttestation(
        tx_id="tx_d",
        peer_address="peer_1",
        timestamp=time.time(),
        signature_hex=None,
    )
    assert ledger.record(att) is False
    assert ledger.attestation_count("tx_d") == 0


def test_require_signatures_false_accepts_unsigned():
    """Default mode accepts unsigned attestations."""
    ledger = TrustLedger(require_signatures=False)
    att = PeerAttestation(
        tx_id="tx_e",
        peer_address="peer_1",
        timestamp=time.time(),
    )
    assert ledger.record(att) is True


def test_signed_attestation_roundtrip():
    """Generate RSA key, sign attestation material, verify via
    record_verified."""
    anchor = IdentityAnchor.generate()
    now = time.time()
    tx_id = "tx_signed_001"

    att_unsigned = PeerAttestation(
        tx_id=tx_id,
        peer_address=anchor.address,
        timestamp=now,
    )
    material = att_unsigned.signing_material()
    sig = anchor.sign(material)

    att_signed = PeerAttestation(
        tx_id=tx_id,
        peer_address=anchor.address,
        timestamp=now,
        signature_hex=sig.hex(),
    )

    jwk = anchor.export_public_jwk()
    ledger = TrustLedger()
    result = ledger.record_verified(att_signed, jwk["n"])
    assert result is True
    assert ledger.attestation_count(tx_id) == 1


def test_invalid_signature_rejected():
    """Attestation with wrong signature is rejected by record_verified."""
    anchor = IdentityAnchor.generate()
    now = time.time()

    att = PeerAttestation(
        tx_id="tx_fake",
        peer_address=anchor.address,
        timestamp=now,
        signature_hex="deadbeef" * 64,
    )

    jwk = anchor.export_public_jwk()
    ledger = TrustLedger()
    result = ledger.record_verified(att, jwk["n"])
    assert result is False
    assert ledger.attestation_count("tx_fake") == 0


# ------------------------------------------------------------------
# PeerAttestation invariants
# ------------------------------------------------------------------


def test_weight_bounds():
    """Weight outside [0, 1] raises ValueError."""
    with pytest.raises(ValueError):
        PeerAttestation(
            tx_id="tx_x",
            peer_address="p",
            timestamp=0.0,
            weight=1.5,
        )


def test_signing_material_deterministic():
    """Same inputs → same signing material."""
    a = PeerAttestation(tx_id="tx1", peer_address="peer1", timestamp=100.0)
    b = PeerAttestation(tx_id="tx1", peer_address="peer1", timestamp=100.0)
    assert a.signing_material() == b.signing_material()

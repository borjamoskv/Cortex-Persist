"""
Tests — ContinuityVerifier and TrustLedger  (Semana 3-4)
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest

from cortex.extensions.swarm.trust_scoring import (
    PeerAttestation,
    TrustLedger,
    attest,
)
from cortex.extensions.swarm.verification import (
    VERIFICATION_HEADER,
    ContinuityVerifier,
    VerificationResult,
)

# ---------------------------------------------------------------------------
# ContinuityVerifier unit tests
# ---------------------------------------------------------------------------


MOCK_NODES_OK = [
    {
        "id": "tx_aaa",
        "owner": {"address": "OWNER_A"},
        "tags": [],
        "block": {"height": 100, "timestamp": 1700000000},
    },
    {
        "id": "tx_bbb",
        "owner": {"address": "OWNER_A"},
        "tags": [],
        "block": {"height": 110, "timestamp": 1700001000},
    },
    {
        "id": "tx_ccc",
        "owner": {"address": "OWNER_A"},
        "tags": [],
        "block": {"height": 120, "timestamp": 1700002000},
    },
]

MOCK_NODES_GAP = [
    {
        "id": "tx_aaa",
        "owner": {"address": "OWNER_A"},
        "tags": [],
        "block": {"height": 100, "timestamp": 1700000000},
    },
    {
        "id": "tx_bbb",
        "owner": {"address": "OWNER_A"},
        "tags": [],
        "block": {"height": 300, "timestamp": 1700010000},  # gap=200 > tolerance=50
    },
]

MOCK_NODES_SPLIT_OWNER = [
    {
        "id": "tx_aaa",
        "owner": {"address": "OWNER_A"},
        "tags": [],
        "block": {"height": 100, "timestamp": 1700000000},
    },
    {
        "id": "tx_bbb",
        "owner": {"address": "OWNER_B"},  # different owner
        "tags": [],
        "block": {"height": 110, "timestamp": 1700001000},
    },
]


class TestContinuityVerifier:
    @pytest.fixture
    def verifier(self) -> ContinuityVerifier:
        return ContinuityVerifier(gap_tolerance_blocks=50)

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_continuous_chain(self, verifier: ContinuityVerifier) -> None:
        with patch.object(verifier, "_graphql_chain", new=AsyncMock(return_value=MOCK_NODES_OK)):
            result = await verifier.verify("fact-001")

        assert result.is_continuous is True
        assert result.chain_length == 3
        assert result.gaps == []
        assert result.trust_score > 0.5
        assert result.error is None

    # ------------------------------------------------------------------
    # Gap detection
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_gap_breaks_continuity(self, verifier: ContinuityVerifier) -> None:
        with patch.object(verifier, "_graphql_chain", new=AsyncMock(return_value=MOCK_NODES_GAP)):
            result = await verifier.verify("fact-002")

        assert result.is_continuous is False
        assert len(result.gaps) == 1
        assert result.gaps[0] == 200

    # ------------------------------------------------------------------
    # Owner mismatch
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_split_owner_breaks_continuity(self, verifier: ContinuityVerifier) -> None:
        with patch.object(
            verifier, "_graphql_chain", new=AsyncMock(return_value=MOCK_NODES_SPLIT_OWNER)
        ):
            result = await verifier.verify("fact-003")

        assert result.is_continuous is False

    # ------------------------------------------------------------------
    # Empty chain
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_chain(self, verifier: ContinuityVerifier) -> None:
        with patch.object(verifier, "_graphql_chain", new=AsyncMock(return_value=[])):
            result = await verifier.verify("fact-empty")

        assert result.is_continuous is False
        assert result.chain_length == 0
        assert result.error is not None

    # ------------------------------------------------------------------
    # GraphQL failure
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_graphql_error(self, verifier: ContinuityVerifier) -> None:
        with patch.object(
            verifier, "_graphql_chain", new=AsyncMock(side_effect=RuntimeError("timeout"))
        ):
            result = await verifier.verify("fact-fail")

        assert result.is_continuous is False
        assert "timeout" in (result.error or "")

    # ------------------------------------------------------------------
    # Verification header
    # ------------------------------------------------------------------

    def test_verification_header_ok(self, verifier: ContinuityVerifier) -> None:
        r = VerificationResult(
            fact_id="fact-001",
            is_continuous=True,
            chain_length=3,
            verified_txs=[],
            trust_score=0.75,
        )
        headers = ContinuityVerifier.build_verification_header(r)
        assert VERIFICATION_HEADER in headers
        val = headers[VERIFICATION_HEADER]
        assert "fact-001" in val
        assert "OK" in val
        assert "0.750" in val

    def test_verification_header_fail(self, verifier: ContinuityVerifier) -> None:
        r = VerificationResult(
            fact_id="fact-002",
            is_continuous=False,
            chain_length=0,
            trust_score=0.0,
        )
        headers = ContinuityVerifier.build_verification_header(r)
        assert "FAIL" in headers[VERIFICATION_HEADER]

    # ------------------------------------------------------------------
    # Trust score mechanics
    # ------------------------------------------------------------------

    def test_score_increases_with_chain_length(self, verifier: ContinuityVerifier) -> None:
        short = ContinuityVerifier._compute_trust_score(2, 0, True)
        long_ = ContinuityVerifier._compute_trust_score(15, 0, True)
        assert long_ > short

    def test_score_penalized_by_gaps(self, verifier: ContinuityVerifier) -> None:
        clean = ContinuityVerifier._compute_trust_score(5, 0, True)
        gapped = ContinuityVerifier._compute_trust_score(5, 2, True)
        assert clean > gapped

    def test_score_penalized_by_owner_mismatch(self, verifier: ContinuityVerifier) -> None:
        stable = ContinuityVerifier._compute_trust_score(5, 0, True)
        unstable = ContinuityVerifier._compute_trust_score(5, 0, False)
        assert stable > unstable

    def test_score_clamped_to_unit_interval(self, verifier: ContinuityVerifier) -> None:
        for (length, gaps, owner) in [
            (0, 10, False),
            (100, 0, True),
        ]:
            s = ContinuityVerifier._compute_trust_score(length, gaps, owner)
            assert 0.0 <= s <= 1.0


# ---------------------------------------------------------------------------
# TrustLedger / PeerAttestation tests
# ---------------------------------------------------------------------------


class TestPeerAttestation:
    def test_rejects_invalid_weight(self) -> None:
        with pytest.raises(ValueError):
            PeerAttestation(tx_id="x", peer_address="y", timestamp=0.0, weight=1.5)

    def test_fingerprint_deterministic(self) -> None:
        a = PeerAttestation(tx_id="tx1", peer_address="p1", timestamp=1000.0)
        b = PeerAttestation(tx_id="tx1", peer_address="p1", timestamp=1000.0)
        assert a.fingerprint == b.fingerprint

    def test_fingerprint_unique(self) -> None:
        a = PeerAttestation(tx_id="tx1", peer_address="p1", timestamp=1000.0)
        b = PeerAttestation(tx_id="tx1", peer_address="p2", timestamp=1000.0)
        assert a.fingerprint != b.fingerprint


class TestTrustLedger:
    @pytest.fixture
    def ledger(self) -> TrustLedger:
        return TrustLedger()

    def test_record_and_count(self, ledger: TrustLedger) -> None:
        a = PeerAttestation(tx_id="tx1", peer_address="p1", timestamp=time.time())
        assert ledger.record(a) is True
        assert ledger.attestation_count("tx1") == 1

    def test_duplicate_rejected(self, ledger: TrustLedger) -> None:
        ts = time.time()
        a1 = PeerAttestation(tx_id="tx1", peer_address="p1", timestamp=ts)
        a2 = PeerAttestation(tx_id="tx1", peer_address="p1", timestamp=ts)
        assert ledger.record(a1) is True
        assert ledger.record(a2) is False
        assert ledger.attestation_count("tx1") == 1

    def test_quorum_gate(self, ledger: TrustLedger) -> None:
        """Score=0 below quorum, >0 at quorum."""
        ts = time.time()
        a1 = PeerAttestation(tx_id="tx1", peer_address="p1", timestamp=ts)
        ledger.record(a1)
        assert ledger.compute_trust("tx1") == 0.0  # 1 peer < quorum=2

        a2 = PeerAttestation(tx_id="tx1", peer_address="p2", timestamp=ts)
        ledger.record(a2)
        assert ledger.compute_trust("tx1") > 0.0

    def test_decay_reduces_score(self, ledger: TrustLedger) -> None:
        old_ts = time.time() - 86_400 * 7  # 7 days ago
        a1 = PeerAttestation(tx_id="tx1", peer_address="p1", timestamp=old_ts)
        a2 = PeerAttestation(tx_id="tx1", peer_address="p2", timestamp=old_ts)
        ledger.record(a1)
        ledger.record(a2)
        old_score = ledger.compute_trust("tx1")

        fresh_ledger = TrustLedger()
        now_ts = time.time()
        fresh_ledger.record(PeerAttestation(tx_id="tx1", peer_address="p1", timestamp=now_ts))
        fresh_ledger.record(PeerAttestation(tx_id="tx1", peer_address="p2", timestamp=now_ts))
        fresh_score = fresh_ledger.compute_trust("tx1")

        assert fresh_score > old_score

    def test_empty_tx_score_zero(self, ledger: TrustLedger) -> None:
        assert ledger.compute_trust("no-such-tx") == 0.0

    def test_summary_shape(self, ledger: TrustLedger) -> None:
        ts = time.time()
        ledger.record(PeerAttestation(tx_id="tx1", peer_address="p1", timestamp=ts))
        ledger.record(PeerAttestation(tx_id="tx1", peer_address="p2", timestamp=ts))
        s = ledger.summary("tx1")
        assert {"tx_id", "attestation_count", "unique_peers", "trust_score"} <= s.keys()

    def test_attest_helper(self, ledger: TrustLedger) -> None:
        result = attest("tx9", "peer-x", ledger)
        assert result is not None
        assert result.tx_id == "tx9"
        # Duplicate → None
        dup = attest("tx9", "peer-x", ledger, timestamp=result.timestamp)
        assert dup is None

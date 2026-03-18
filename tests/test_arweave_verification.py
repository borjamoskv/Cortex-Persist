"""
Tests — ArweaveClient + ContinuityVerifier (via verification.py)

Migrated from verifier.py (legacy verify_chain API) to the unified
verification.py (verify → VerificationResult).  Purges the ghost.
"""

import time
from unittest.mock import AsyncMock, patch

import pytest

from cortex.engine.causality import EpistemicStatus, LedgerEvent
from cortex.extensions.swarm.verification import ContinuityVerifier


@pytest.mark.asyncio
async def test_continuity_verifier_success():
    """Verify that a chronological chain is correctly validated."""
    verifier = ContinuityVerifier()

    mock_nodes = [
        {
            "id": "tx1",
            "owner": {"address": "OWNER_A"},
            "tags": [{"name": "Cortex-Timestamp", "value": "1000"}],
            "block": {"height": 100, "timestamp": 1700000000},
        },
        {
            "id": "tx2",
            "owner": {"address": "OWNER_A"},
            "tags": [{"name": "Cortex-Timestamp", "value": "1050"}],
            "block": {"height": 110, "timestamp": 1700001000},
        },
        {
            "id": "tx3",
            "owner": {"address": "OWNER_A"},
            "tags": [{"name": "Cortex-Timestamp", "value": "1100"}],
            "block": {"height": 120, "timestamp": 1700002000},
        },
    ]

    with patch.object(verifier, "_graphql_chain", new=AsyncMock(return_value=mock_nodes)):
        result = await verifier.verify("fact-123")

    assert result.is_continuous is True
    assert result.chain_length == 3


@pytest.mark.asyncio
async def test_continuity_verifier_broken_timeline():
    """Verify that a backwards-in-time timestamp tag breaks continuity (Memory Fork guard)."""
    verifier = ContinuityVerifier()

    mock_nodes = [
        {
            "id": "tx1",
            "owner": {"address": "OWNER_A"},
            "tags": [{"name": "Cortex-Timestamp", "value": "1000"}],
            "block": {"height": 100, "timestamp": 1700000000},
        },
        {
            "id": "tx2",
            "owner": {"address": "OWNER_A"},
            "tags": [{"name": "Cortex-Timestamp", "value": "1100"}],
            "block": {"height": 110, "timestamp": 1700001000},
        },
        {
            "id": "tx3",
            "owner": {"address": "OWNER_A"},
            # Time-travel: 1050 < 1100 → fork detected
            "tags": [{"name": "Cortex-Timestamp", "value": "1050"}],
            "block": {"height": 120, "timestamp": 1700002000},
        },
    ]

    with patch.object(verifier, "_graphql_chain", new=AsyncMock(return_value=mock_nodes)):
        result = await verifier.verify("fact-fork")

    assert result.is_continuous is False


@pytest.mark.asyncio
async def test_continuity_verifier_empty():
    """Verify that an empty chain returns a failed VerificationResult."""
    verifier = ContinuityVerifier()

    with patch.object(verifier, "_graphql_chain", new=AsyncMock(return_value=[])):
        result = await verifier.verify("fact-404")

    assert result.is_continuous is False
    assert result.chain_length == 0
    assert result.error is not None


def test_peer_attestation_trust_score():
    """Verify that peer attestations accumulate trust score on LedgerEvent."""
    event = LedgerEvent(
        event_id="fact-123",
        parent_ids=[],
        status=EpistemicStatus.TEST_PASSED,
        trust_score=0.5,
        created_at=str(time.time()),
        tainted=False,
    )

    assert event.trust_score == 0.5
    assert len(event.peer_attestations) == 0

    event.add_attestation("rx_123")
    assert event.trust_score == 0.6
    assert "rx_123" in event.peer_attestations

    # Duplicate attestation — idempotent
    event.add_attestation("rx_123")
    assert event.trust_score == 0.6

    # Ceiling at 1.0
    for i in range(10):
        event.add_attestation(f"rx_new_{i}")

    assert event.trust_score == 1.0

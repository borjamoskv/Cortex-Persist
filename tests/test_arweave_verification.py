import pytest
import time
from unittest.mock import AsyncMock, patch
from cortex.extensions.swarm.arweave_client import ArweaveClient
from cortex.extensions.swarm.verifier import ContinuityVerifier
from cortex.extensions.swarm.identity import IdentityAnchor
from cortex.engine.causality import LedgerEvent, EpistemicStatus

@pytest.mark.asyncio
async def test_continuity_verifier_success():
    """Verify that a chronological chain is correctly validated."""
    verifier = ContinuityVerifier()
    
    mock_tx_nodes = [
        {"id": "tx1", "tags": [{"name": "Cortex-Timestamp", "value": "1000"}]},
        {"id": "tx2", "tags": [{"name": "Cortex-Timestamp", "value": "1050"}]},
        {"id": "tx3", "tags": [{"name": "Cortex-Timestamp", "value": "1100"}]},
    ]
    
    with patch.object(verifier.arweave_client, "query_handoff_chain", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = mock_tx_nodes
        result = await verifier.verify_chain("fact-123")
        assert result is True

@pytest.mark.asyncio
async def test_continuity_verifier_broken_timeline():
    """Verify that a backwards-in-time chain is rejected."""
    verifier = ContinuityVerifier()
    
    # Tx3 timestamp is older than Tx2 (Time travel attack / Memory Fork)
    mock_tx_nodes = [
        {"id": "tx1", "tags": [{"name": "Cortex-Timestamp", "value": "1000"}]},
        {"id": "tx2", "tags": [{"name": "Cortex-Timestamp", "value": "1100"}]},
        {"id": "tx3", "tags": [{"name": "Cortex-Timestamp", "value": "1050"}]},
    ]
    
    with patch.object(verifier.arweave_client, "query_handoff_chain", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = mock_tx_nodes
        result = await verifier.verify_chain("fact-123")
        assert result is False

@pytest.mark.asyncio
async def test_continuity_verifier_empty():
    """Verify that an empty chain returns False."""
    verifier = ContinuityVerifier()
    
    with patch.object(verifier.arweave_client, "query_handoff_chain", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = []
        result = await verifier.verify_chain("fact-404")
        assert result is False

def test_peer_attestation_trust_score():
    """Verify that peer attestations increase the trust score dynamically."""
    event = LedgerEvent(
        event_id="fact-123",
        parent_ids=[],
        status=EpistemicStatus.TEST_PASSED,
        trust_score=0.5,
        created_at=str(time.time()),
        tainted=False
    )
    
    assert event.trust_score == 0.5
    assert len(event.peer_attestations) == 0
    
    # Add first attestation
    event.add_attestation("rx_123")
    assert event.trust_score == 0.6
    assert "rx_123" in event.peer_attestations
    
    # Add duplicate attestation (should be ignored)
    event.add_attestation("rx_123")
    assert event.trust_score == 0.6
    
    # Add multiple to hit maximum bound
    for i in range(10):
        event.add_attestation(f"rx_new_{i}")
        
    assert event.trust_score == 1.0  # Should be capped at 1.0

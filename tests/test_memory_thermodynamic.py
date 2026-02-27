"""Tests for CORTEX Thermodynamic Memory Engine."""

from unittest.mock import AsyncMock, patch

import pytest

from cortex.memory.engrams import CortexSemanticEngram
from cortex.memory.homeostasis import DynamicSynapseUpdate, EntropyPruner


@pytest.fixture
def mock_vector_store():
    store = AsyncMock()
    return store


def test_engram_decay():
    """Test that engrams decay over time simulated."""
    engram = CortexSemanticEngram(
        id="test-1",
        tenant_id="tenant-1",
        project_id="test",
        content="Testing decay",
        embedding=[0.1, 0.2, 0.3],
        energy_level=1.0,
    )

    # Assert initialized correctly
    assert engram.energy_level == 1.0

    # Simulate a time passing of 10 days
    # (decay_rate_per_day = 0.05, 10 days -> 10 * 0.05 = 0.5)
    with patch("time.time", return_value=engram.last_accessed + 86400 * 10):
        decayed_energy = engram.compute_decay(decay_rate_per_day=0.05)
        # Account for float inaccuracies, wait, it computes dynamically
        assert 0.49 <= decayed_energy <= 0.51


def test_engram_access_ltp():
    """Test that accessing an engram strengthens its energy."""
    engram = CortexSemanticEngram(
        id="test-2",
        tenant_id="tenant-1",
        project_id="test",
        content="Testing LTP",
        embedding=[0.1, 0.2, 0.3],
        energy_level=0.5,
    )

    # Access it
    engram.access(boost=0.3)
    assert engram.energy_level == 0.8

    # Maximum ceiling
    engram.access(boost=0.5)
    assert engram.energy_level == 1.0


@pytest.mark.asyncio
async def test_entropy_pruner_deletes_low_energy(mock_vector_store):
    """Test that EntropyPruner removes depleted engrams."""
    # Create one healthy engram and one depleted
    healthy = CortexSemanticEngram(
        id="healthy", tenant_id="t-1", project_id="test", content="H", embedding=[0.1], energy_level=0.9
    )
    depleted = CortexSemanticEngram(
        id="depleted", tenant_id="t-1", project_id="test", content="D", embedding=[0.1], energy_level=0.1
    )

    mock_vector_store.scan_engrams.return_value = [healthy, depleted]
    pruner = EntropyPruner(vector_store=mock_vector_store, atp_threshold=0.2)

    pruned_count = await pruner.prune_cycle(tenant_id="t-1")

    assert pruned_count == 1
    mock_vector_store.delete.assert_called_once_with("depleted")


@pytest.mark.asyncio
async def test_dynamic_synapse_update_strengthens(mock_vector_store):
    """Test that DynamicSynapseUpdate applies LTP efficiently."""
    engram = CortexSemanticEngram(
        id="weak", tenant_id="t-1", project_id="test", content="W", embedding=[0.1], energy_level=0.4
    )
    mock_vector_store.get_fact.return_value = engram

    synapse = DynamicSynapseUpdate(vector_store=mock_vector_store)
    result = await synapse.reinforce("weak", boost=0.4)

    assert result is True
    # Verify upsert was called with updated engram
    mock_vector_store.upsert.assert_called_once()
    upserted_args = mock_vector_store.upsert.call_args[0][0]
    assert upserted_args.energy_level == 0.8
    assert upserted_args.id == "weak"

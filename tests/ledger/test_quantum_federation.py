"""
Tests for Quantum Bridge Federation (Múltiples Soles).
Verifies that multiple nodes entangling facts can sync their ledger state
asynchronously without requiring a central database.
"""

import asyncio

import pytest

from cortex.ledger.quantum_bridge import EntanglementBus, QuantumLedgerBridge, QuantumState


@pytest.mark.asyncio
async def test_quantum_federation_entanglement():
    """
    Test that 3 independent nodes connected to the same EntanglementBus
    can sync fact collapses.
    """
    bus = EntanglementBus()

    # Create 3 distributed nodes
    node_a = QuantumLedgerBridge(node_id="node_a", bus=bus)
    node_b = QuantumLedgerBridge(node_id="node_b", bus=bus)
    node_c = QuantumLedgerBridge(node_id="node_c", bus=bus)

    # Register the same fact in superposition on all nodes
    fact_id = "fact_kardashev_leap"
    node_a.register_fact(fact_id)
    node_b.register_fact(fact_id)
    node_c.register_fact(fact_id)

    # Verify initial state
    assert node_a._registry[fact_id].state == QuantumState.SUPERPOSITION
    assert node_b._registry[fact_id].state == QuantumState.SUPERPOSITION

    # Node A measures (collapses) the fact
    measured = await node_a.apply_observation(fact_id)
    assert measured is True

    # Yield control to the event loop so the EntanglementBus broadcasts
    await asyncio.sleep(0.1)

    # Verify that Node B and Node C synchronized the collapse
    assert node_b._registry[fact_id].state == QuantumState.COLLAPSED
    assert node_c._registry[fact_id].state == QuantumState.COLLAPSED

    # Verify they share the same cryptographic hash signature
    assert node_a._registry[fact_id].hash_signature is not None
    assert node_a._registry[fact_id].hash_signature == node_b._registry[fact_id].hash_signature
    assert node_b._registry[fact_id].hash_signature == node_c._registry[fact_id].hash_signature

    # Cleanup listeners
    await node_a.stop()
    await node_b.stop()
    await node_c.stop()


@pytest.mark.asyncio
async def test_quantum_bell_state_cascade():
    """
    Test that if Fact A and Fact B are entangled (Bell state),
    measuring Fact A will cause a cascading measurement of Fact B across the swarm.
    """
    bus = EntanglementBus()
    node_a = QuantumLedgerBridge(node_id="alpha", bus=bus)
    node_b = QuantumLedgerBridge(node_id="beta", bus=bus)

    # Node A and B know about two facts
    node_a.register_fact("fact_1")
    node_a.register_fact("fact_2")
    node_b.register_fact("fact_1")
    node_b.register_fact("fact_2")

    # Node B entangles fact_1 with fact_2 locally
    node_b.entangle("fact_1", "fact_2")
    assert node_b._registry["fact_1"].state == QuantumState.ENTANGLED
    assert node_b._registry["fact_2"].state == QuantumState.ENTANGLED

    # Node A measures fact_1
    await node_a.apply_observation("fact_1")

    # Wait for propagation
    await asyncio.sleep(0.1)

    # Node B should have received fact_1's collapse.
    # Because fact_1 and fact_2 were entangled on Node B, fact_2 should also collapse!
    assert node_b._registry["fact_1"].state == QuantumState.COLLAPSED
    assert node_b._registry["fact_2"].state == QuantumState.COLLAPSED

    # Cleanup listeners
    await node_a.stop()
    await node_b.stop()

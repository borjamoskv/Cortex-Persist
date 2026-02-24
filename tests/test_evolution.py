import pytest
import asyncio
from cortex.evolution.engine import EvolutionEngine
from cortex.evolution.quantum_memory import QuantumMemory

@pytest.mark.asyncio
async def test_paradox_loop():
    engine = EvolutionEngine(context_snapshot={"facts": 35})
    solutions = await engine.paradox_loop("Agent Memory")
    assert len(solutions) == 3
    assert "Quantum Ghost Memory" in solutions[0]

@pytest.mark.asyncio
async def test_quantum_memory_latency():
    memory = QuantumMemory()
    success = await memory.store_with_zero_latency("test_key", "sovereign_data")
    assert success is True
    val = await memory.retrieve_entangled("test_key")
    assert val == "sovereign_data"
    assert memory.measure_entropy() > 0

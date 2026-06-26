# [C5-REAL] Exergy-Maximized
"""
Tests for CORTEX-SWARM-100 architecture and AsyncSignalBus implementation.
Validates O(1) parallel racing and collision-free P2P sync.
"""

import asyncio
import time

import pytest

from cortex.engine.swarm.legion import AsyncSignalBus, Squadron, SwarmAgent, SwarmSignal


class MockAgent(SwarmAgent):
    """A simulated agent that sleeps and emits a signal."""

    async def execute(self, target: str) -> SwarmSignal:
        await asyncio.sleep(0.1)  # Simulate network/LLM latency
        return SwarmSignal(
            agent_id=self.agent_id,
            target=target,
            status="SUCCESS",
            payload={
                "result": "ok",
                "proof": "Proof: { Base: 'Test', Range: [0,1], Confidence: C5-REAL }",
            },
            metrics={"latency": 100},
        )


class MockSquadron(Squadron):
    """Squadron for testing the 100-agent deployment."""

    SQUAD_NAME = "MOCK_SQUAD_100"
    REPLICAS = 100

    def _create_agent(self, agent_id: str) -> SwarmAgent:
        return MockAgent(agent_id, self.bus, self.engine)

    async def _map(self, target_pattern: str | None = None) -> list[str]:
        # Generate 100 phantom targets
        return [f"target_{i}" for i in range(100)]


@pytest.mark.asyncio
async def test_async_signal_bus_emits() -> None:
    """Test standard Signal emission to the bus."""
    bus = AsyncSignalBus()

    # 1. Emit normal signal
    await bus.emit(SwarmSignal("id", "target", "SUCCESS", {"a": 1}, {}))

    # 2. Emit empty payload signal (enforcing VOID invariant)
    signal = SwarmSignal("id2", "target2", "UNKNOWN", {}, {})
    await bus.emit(signal)

    all_signals = await bus.get_all()
    assert len(all_signals) == 2
    assert all_signals[0].status == "SUCCESS"
    assert all_signals[1].status == "VOID"  # System should rewrite this


@pytest.mark.asyncio
async def test_swarm_deployment_100() -> None:
    """Test 100-agent deployment and parallel execution latency (O(1))."""
    squadron = MockSquadron()

    start_time = time.monotonic()
    result = await squadron.deploy("phantom_pattern")
    end_time = time.monotonic()

    # Validation: 100 signals completed
    assert result["squadron"] == "MOCK_SQUAD_100"
    assert result["total_signals"] == 100
    assert result["success"] == 100

    # Validation: O(1) Execution Time
    # 100 agents doing 0.1s of work in parallel should take ~0.1s total (plus overhead).
    # If synchronous, it would take 10 seconds.
    # So we assert it finishes in less than 0.5s.
    duration = end_time - start_time
    assert duration < 0.5, f"Swarm 100 deployment was too slow: {duration}s"

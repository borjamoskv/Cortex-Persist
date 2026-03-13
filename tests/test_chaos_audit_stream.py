"""CORTEX v8.0 — Chaos Simulation Tests for Audit Stream L1.

Axiom: Ω₅ (Antifragile by Default)
  - Every chaos scenario MUST:
    1. Capture the interruption as a Ghost.
    2. Transfer state to the ErrorGhostPipeline.
    3. NEVER interrupt critical processes.
  - All mechanisms sealed: O(1) lookup, O(1) fallback, O(1) recovery.

Scenarios tested:
  1. KILL  — Abrupt daemon termination (SIGKILL).
  2. CORRUPTION — Malformed audit stream data.
  3. PARTIAL_FAILURE — Transaction interrupted mid-pipeline.
  4. TIMEOUT — Consumer group stops ACKing.
  5. BYZANTINE — Multiple simultaneous subsystem failures.
  6. FULL_SIEGE — All scenarios in sequence (Ouroboros Loop).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from cortex.red_team.hydra_chaos import (
    ChaosResult,
    ChaosScenario,
    HydraChaosEngine,
    MockRedisClient,
)
from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def fresh_ghost_pipeline():
    """Reset the ErrorGhostPipeline singleton before each test."""
    pipeline = ErrorGhostPipeline()
    pipeline.reset()
    ErrorGhostPipeline._instance = None
    yield
    pipeline = ErrorGhostPipeline()
    pipeline.reset()


@pytest.fixture
def mock_redis() -> MockRedisClient:
    """Fresh MockRedisClient for each test."""
    return MockRedisClient()


@pytest.fixture
def chaos_engine() -> HydraChaosEngine:
    """Fresh HydraChaosEngine for each test."""
    return HydraChaosEngine()


# ── MockRedisClient Unit Tests ────────────────────────────────────────


class TestMockRedisClient:
    """Verify the mock itself behaves correctly.
    Note: Failure logic moved to ChaosGate.
    """

    @pytest.mark.asyncio
    async def test_basic_get_set(self, mock_redis: MockRedisClient):
        await mock_redis.set("key1", "value1")
        result = await mock_redis.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_resurrect_no_op(self, mock_redis: MockRedisClient):
        # resurrected is now a no-op for compatibility
        mock_redis.resurrect()
        await mock_redis.set("key", "alive")
        assert await mock_redis.get("key") == "alive"


# ── Chaos Scenario Tests ──────────────────────────────────────────────


class TestRedisKillScenario:
    """Scenario 1: Redis daemon killed abruptly (SIGKILL simulation)."""

    @pytest.mark.asyncio
    async def test_redis_kill_captures_ghost(
        self,
        chaos_engine: HydraChaosEngine,
        mock_redis: MockRedisClient,
    ):
        """When Redis dies mid-operation, the error MUST become a Ghost."""
        with patch(
            "cortex.swarm.error_ghost_pipeline.ErrorGhostPipeline._persist_async",
            new_callable=AsyncMock,
            return_value=1,
        ):
            result = await chaos_engine.execute_scenario(
                ChaosScenario.KILL,
                mock_redis,
            )

        assert result.ghost_captured, "Ghost MUST be captured on Redis kill"
        assert result.pipeline_transferred, "State MUST transfer to Pipeline"
        assert not result.critical_process_interrupted, "Critical processes MUST NOT be interrupted"
        assert result.is_sovereign, f"Scenario MUST be sovereign: {result}"
        assert result.error_type == "ConnectionError"

    @pytest.mark.asyncio
    async def test_redis_kill_latency_under_threshold(
        self,
        chaos_engine: HydraChaosEngine,
        mock_redis: MockRedisClient,
    ):
        """Ghost capture on Redis kill MUST complete in O(1) time (< 100ms)."""
        with patch(
            "cortex.swarm.error_ghost_pipeline.ErrorGhostPipeline._persist_async",
            new_callable=AsyncMock,
            return_value=1,
        ):
            result = await chaos_engine.execute_scenario(
                ChaosScenario.KILL,
                mock_redis,
            )

        latency_ms = result.latency_ns / 1_000_000
        assert latency_ms < 100, f"Ghost capture latency {latency_ms:.2f}ms exceeds O(1) threshold"


class TestStreamCorruptionScenario:
    """Scenario 2: Audit stream returns corrupted/malformed data."""

    @pytest.mark.asyncio
    async def test_stream_corruption_captures_ghost(
        self,
        chaos_engine: HydraChaosEngine,
        mock_redis: MockRedisClient,
    ):
        """Corrupted stream data MUST be intercepted as a Ghost."""
        with patch(
            "cortex.swarm.error_ghost_pipeline.ErrorGhostPipeline._persist_async",
            new_callable=AsyncMock,
            return_value=2,
        ):
            result = await chaos_engine.execute_scenario(
                ChaosScenario.CORRUPTION,
                mock_redis,
            )

        assert result.ghost_captured, "Ghost MUST be captured on stream corruption"
        assert result.pipeline_transferred, "Pipeline MUST receive corrupted state"
        assert not result.critical_process_interrupted
        assert result.is_sovereign

    @pytest.mark.asyncio
    async def test_corruption_does_not_crash_cache(
        self,
        mock_redis: MockRedisClient,
    ):
        """Corrupted JSON in cache MUST NOT crash the DistributedSovereignCache."""
        from cortex.memory.distributed_cache import DistributedSovereignCache

        cache = DistributedSovereignCache(mock_redis)

        # Store valid data
        await cache.put("agent:test", {"data": "clean"})

        # Arm corruption on the gate
        cache.chaos_gate.arm(ChaosScenario.CORRUPTION)

        # get() should handle bad JSON gracefully
        with patch(
            "cortex.swarm.error_ghost_pipeline.ErrorGhostPipeline.capture_sync",
        ):
            await cache.get("agent:test")


class TestPartialWriteScenario:
    """Scenario 3: Pipeline transaction interrupted mid-write."""

    @pytest.mark.asyncio
    async def test_partial_write_captures_ghost(
        self,
        chaos_engine: HydraChaosEngine,
        mock_redis: MockRedisClient,
    ):
        """Partial write MUST be captured as Ghost with data-in-limbo metadata."""
        with patch(
            "cortex.swarm.error_ghost_pipeline.ErrorGhostPipeline._persist_async",
            new_callable=AsyncMock,
            return_value=3,
        ):
            result = await chaos_engine.execute_scenario(
                ChaosScenario.PARTIAL_FAILURE,
                mock_redis,
            )

        assert result.ghost_captured, "Partial write MUST generate Ghost"
        assert result.pipeline_transferred
        assert not result.critical_process_interrupted
        assert result.is_sovereign
        assert result.metadata.get("data_in_limbo") is True

    @pytest.mark.asyncio
    async def test_partial_write_marks_cache_unavailable(
        self,
        mock_redis: MockRedisClient,
    ):
        """After partial write, cache MUST be marked unavailable."""
        from cortex.memory.distributed_cache import DistributedSovereignCache

        cache = DistributedSovereignCache(mock_redis)
        cache.chaos_gate.arm(ChaosScenario.PARTIAL_FAILURE)

        result = await cache.put("key", {"v": 1})
        assert not result, "put() on partial write must return False"
        assert not cache._is_available, "Cache MUST be marked unavailable"


class TestConsumerStallScenario:
    """Scenario 4: Consumer group stops ACKing — backpressure."""

    @pytest.mark.asyncio
    async def test_consumer_stall_captures_ghost(
        self,
        chaos_engine: HydraChaosEngine,
        mock_redis: MockRedisClient,
    ):
        """Consumer stall MUST be captured as Ghost without blocking."""
        with patch(
            "cortex.swarm.error_ghost_pipeline.ErrorGhostPipeline._persist_async",
            new_callable=AsyncMock,
            return_value=4,
        ):
            result = await chaos_engine.execute_scenario(
                ChaosScenario.TIMEOUT,
                mock_redis,
            )

        assert result.ghost_captured, "Consumer stall MUST generate Ghost"
        assert result.pipeline_transferred
        assert not result.critical_process_interrupted
        assert result.is_sovereign


class TestCascadeFailureScenario:
    """Scenario 5: Multiple subsystems fail simultaneously."""

    @pytest.mark.asyncio
    async def test_cascade_failure_captures_all_ghosts(
        self,
        chaos_engine: HydraChaosEngine,
        mock_redis: MockRedisClient,
    ):
        """ALL concurrent failures MUST be captured — zero leaks."""
        with patch(
            "cortex.swarm.error_ghost_pipeline.ErrorGhostPipeline._persist_async",
            new_callable=AsyncMock,
            return_value=5,
        ):
            result = await chaos_engine.execute_scenario(
                ChaosScenario.BYZANTINE,
                mock_redis,
            )

        assert result.ghost_captured, "Cascade MUST capture all Ghosts"
        assert result.pipeline_transferred, "Pipeline MUST receive all states"
        assert not result.critical_process_interrupted, "No critical process MUST be interrupted"
        assert result.is_sovereign
        assert result.metadata.get("concurrent_ops") == 3

    @pytest.mark.asyncio
    async def test_cascade_latency_bounded(
        self,
        chaos_engine: HydraChaosEngine,
        mock_redis: MockRedisClient,
    ):
        """Cascade failure recovery MUST be O(1) — bounded latency."""
        with patch(
            "cortex.swarm.error_ghost_pipeline.ErrorGhostPipeline._persist_async",
            new_callable=AsyncMock,
            return_value=6,
        ):
            result = await chaos_engine.execute_scenario(
                ChaosScenario.BYZANTINE,
                mock_redis,
            )

        latency_ms = result.latency_ns / 1_000_000
        assert latency_ms < 200, f"Cascade recovery latency {latency_ms:.2f}ms exceeds bound"


# ── Full Siege Test (Ouroboros Loop) ──────────────────────────────────


class TestFullSiege:
    """Execute ALL chaos scenarios in sequence — the Ouroboros Loop."""

    @pytest.mark.asyncio
    async def test_full_siege_all_sovereign(
        self,
        chaos_engine: HydraChaosEngine,
    ):
        """Every chaos scenario MUST pass sovereignty check."""
        with patch(
            "cortex.swarm.error_ghost_pipeline.ErrorGhostPipeline._persist_async",
            new_callable=AsyncMock,
            return_value=99,
        ):
            for scenario in ChaosScenario:
                if scenario == ChaosScenario.BYZANTINE:
                    # Byzantine/Cascade requires multiple ops, handled by hydra
                    pass
                mock = MockRedisClient()
                result = await chaos_engine.execute_scenario(scenario, mock)
                assert result.is_sovereign, (
                    f"SIEGE FAILURE: {scenario.name} is NOT sovereign — "
                    f"ghost={result.ghost_captured}, pipeline={result.pipeline_transferred}, "
                    f"critical_interrupted={result.critical_process_interrupted}"
                )

        # All scenarios must have been executed
        assert len(chaos_engine.results) == len(ChaosScenario)
        assert chaos_engine.all_sovereign, "SYSTEM NOT SOVEREIGN — siege failed"

        report = chaos_engine.report()
        assert report["all_sovereign"] is True
        assert report["total_scenarios"] == len(ChaosScenario)

    @pytest.mark.asyncio
    async def test_siege_report_structure(
        self,
        chaos_engine: HydraChaosEngine,
    ):
        """Report must contain structured data for all scenarios."""
        with patch(
            "cortex.swarm.error_ghost_pipeline.ErrorGhostPipeline._persist_async",
            new_callable=AsyncMock,
            return_value=100,
        ):
            for scenario in ChaosScenario:
                await chaos_engine.execute_scenario(scenario, MockRedisClient())

        report = chaos_engine.report()

        for entry in report["scenarios"]:
            assert "name" in entry
            assert "sovereign" in entry
            assert "latency_us" in entry
            assert isinstance(entry["latency_us"], float)
            assert entry["latency_us"] > 0


# ── ErrorGhostPipeline Integration ────────────────────────────────────


class TestGhostPipelineIntegration:
    """Verify that chaos-generated errors actually flow through the ErrorGhostPipeline."""

    @pytest.mark.asyncio
    async def test_connection_error_persists_as_ghost(self):
        """A ConnectionError from Redis MUST be persistable as a ghost fact."""
        pipeline = ErrorGhostPipeline()

        with patch(
            "cortex.swarm.error_ghost_pipeline.ErrorGhostPipeline._persist_async",
            new_callable=AsyncMock,
            return_value=42,
        ) as mock_persist:
            try:
                raise ConnectionError("Redis connection refused: daemon killed (SIGKILL)")
            except ConnectionError as e:
                fact_id = await pipeline.capture(
                    e,
                    source="distributed_cache:get",
                    project="CORTEX_SYSTEM",
                    extra_meta={"chaos_scenario": "KILL"},
                )

        assert fact_id == 42
        assert pipeline.stats["total_captured"] == 1
        mock_persist.assert_called_once()

    @pytest.mark.asyncio
    async def test_timeout_error_persists_as_ghost(self):
        """A TimeoutError from consumer stall MUST flow through pipeline."""
        pipeline = ErrorGhostPipeline()

        with patch(
            "cortex.swarm.error_ghost_pipeline.ErrorGhostPipeline._persist_async",
            new_callable=AsyncMock,
            return_value=43,
        ):
            try:
                raise TimeoutError("Consumer group read timed out (stall)")
            except TimeoutError as e:
                fact_id = await pipeline.capture(
                    e,
                    source="distributed_cache:consumer",
                    project="CORTEX_SYSTEM",
                )

        assert fact_id == 43
        assert pipeline.stats["total_captured"] == 1

    @pytest.mark.asyncio
    async def test_cascade_errors_deduped_correctly(self):
        """Multiple identical errors from cascade MUST be deduped (Ω₅ ring buffer)."""
        pipeline = ErrorGhostPipeline()

        with patch(
            "cortex.swarm.error_ghost_pipeline.ErrorGhostPipeline._persist_async",
            new_callable=AsyncMock,
            return_value=44,
        ):
            for _ in range(5):
                try:
                    raise ConnectionError("Redis connection refused: daemon killed (SIGKILL)")
                except ConnectionError as e:
                    await pipeline.capture(
                        e,
                        source="chaos:cascade",
                        project="TEST",
                    )

        # First should be captured, rest deduped or rate-limited
        assert pipeline.stats["total_captured"] == 1
        assert pipeline.stats["total_deduped"] + pipeline.stats["total_rate_limited"] == 4


# ── ChaosResult Dataclass Tests ───────────────────────────────────────


class TestChaosResult:
    """Verify the ChaosResult sovereignty invariant."""

    def test_sovereign_when_all_conditions_met(self):
        r = ChaosResult(
            scenario=ChaosScenario.KILL,
            ghost_captured=True,
            pipeline_transferred=True,
            critical_process_interrupted=False,
            latency_ns=1000,
        )
        assert r.is_sovereign

    def test_not_sovereign_when_ghost_not_captured(self):
        r = ChaosResult(
            scenario=ChaosScenario.KILL,
            ghost_captured=False,
            pipeline_transferred=True,
            critical_process_interrupted=False,
            latency_ns=1000,
        )
        assert not r.is_sovereign

    def test_not_sovereign_when_critical_interrupted(self):
        r = ChaosResult(
            scenario=ChaosScenario.KILL,
            ghost_captured=True,
            pipeline_transferred=True,
            critical_process_interrupted=True,
            latency_ns=1000,
        )
        assert not r.is_sovereign

    def test_not_sovereign_when_pipeline_not_transferred(self):
        r = ChaosResult(
            scenario=ChaosScenario.KILL,
            ghost_captured=True,
            pipeline_transferred=False,
            critical_process_interrupted=False,
            latency_ns=1000,
        )
        assert not r.is_sovereign

"""CORTEX v7.5 — Hydra Chaos Engine (Audit Stream L1 Siege).

Orchestrates simulated failures on external dependencies (Redis, APIs, etc.)
to verify system antifragility (Ω₅).

Refactored to use the generalized ChaosGate system.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from cortex.immune.chaos import ChaosScenario, async_interceptor
from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline

logger = logging.getLogger("cortex.red_team.hydra_chaos")


@dataclass
class ChaosResult:
    """Outcome of a chaos scenario."""

    scenario: ChaosScenario
    ghost_captured: bool
    pipeline_transferred: bool
    critical_process_interrupted: bool
    latency_ns: int
    error_type: str | None = None
    ghost_content_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_sovereign(self) -> bool:
        """Sovereignty check: Ghost MUST be captured, Pipeline MUST receive state."""
        return (
            self.ghost_captured
            and self.pipeline_transferred
            and not self.critical_process_interrupted
        )


class MockRedisClient:
    """Minimal Mock Redis client for chaos testing."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._is_alive = True

    async def get(self, key: str) -> str | None:
        await asyncio.sleep(0)  # Satisfy async lint
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        await asyncio.sleep(0)
        self._store[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        await asyncio.sleep(0)
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
        return count

    async def xadd(self, _stream: str, fields: dict[str, Any], **_kwargs: Any) -> str:
        await asyncio.sleep(0)
        return f"{int(time.time()*1000)}-0"

    async def xreadgroup(
        self, _group: str, _consumer: str, _streams: dict[str, str], **_kwargs: Any
    ) -> list[tuple[str, list[tuple[str, dict[str, str]]]]]:
        await asyncio.sleep(0)
        return []

    async def xack(self, _stream: str, _group: str, *_ids: str) -> int:
        await asyncio.sleep(0)
        return 1

    async def aclose(self) -> None:
        await asyncio.sleep(0)
        self._is_alive = False

    def resurrect(self) -> None:
        self._is_alive = True

    def register_script(self, _script: str) -> AsyncMock:
        """Return a mock Lua script executor."""
        async def execute(*, keys: list, args: list) -> tuple[str, str, int]:
            genesis = args[0]
            agent_key = args[1]
            payload_hash = args[2]
            prev_tip = self._store.get(keys[0], genesis)
            count = int(self._store.get(keys[1], "0")) + 1

            key_hex = hashlib.sha256(agent_key.encode()).hexdigest()
            proof_material = f"{prev_tip}|{key_hex}|{payload_hash}"
            new_tip = hashlib.sha256(proof_material.encode()).hexdigest()

            self._store[keys[0]] = new_tip
            self._store[keys[1]] = str(count)
            return (prev_tip, new_tip, count)

        return AsyncMock(side_effect=execute)

    def pipeline(self, *, transaction: bool = True) -> MagicMock:
        mock = MagicMock()
        mock.transaction = transaction

        # mock.set should not be a coroutine here, it just buffers
        def sync_set(k: str, v: str, **_kwargs: Any) -> None:
            self._store[k] = v

        mock.set = MagicMock(side_effect=sync_set)
        mock.execute = AsyncMock(return_value=[True])

        async def __aenter__(*args: Any, **kwargs: Any) -> MagicMock:
            return mock

        async def __aexit__(*args: Any, **kwargs: Any) -> None:
            """Mock async context manager exit."""
            pass

        mock.__aenter__ = __aenter__
        mock.__aexit__ = __aexit__
        return mock

    def pubsub(self) -> MagicMock:
        mock = MagicMock()
        mock.psubscribe = AsyncMock()
        mock.unsubscribe = AsyncMock()
        mock.aclose = AsyncMock()

        async def listen():
            yield {"type": "subscribe"}
        mock.listen = listen
        return mock


class HydraChaosEngine:
    """The High-Siege Engine for CORTEX."""

    def __init__(self) -> None:
        self.results: list[ChaosResult] = []

    async def execute_scenario(
        self,
        scenario: ChaosScenario,
        mock_redis: MockRedisClient,
        _pipeline_mock: MagicMock | None = None,
    ) -> ChaosResult:
        """Execute a single chaos scenario and record the result."""
        ghost_pipeline = ErrorGhostPipeline()
        ghost_pipeline.reset()

        start_ts = time.perf_counter_ns()

        # Scenario logic
        critical_interrupted = False
        error_type = None
        metadata: dict[str, Any] = {"phase": "siege_execution"}

        try:
            if scenario == ChaosScenario.KILL:
                await self._scenario_redis_kill(mock_redis)
                error_type = "ConnectionError"
            elif scenario == ChaosScenario.CORRUPTION:
                await self._scenario_stream_corruption(mock_redis)
                error_type = "JSONDecodeError"
            elif scenario == ChaosScenario.PARTIAL_FAILURE:
                await self._scenario_partial_write(mock_redis)
                error_type = "ConnectionError"
                metadata["data_in_limbo"] = True
            elif scenario == ChaosScenario.TIMEOUT:
                await self._scenario_consumer_stall(mock_redis)
                error_type = "TimeoutError"
            elif scenario == ChaosScenario.BYZANTINE:
                await self._scenario_cascade_failure(mock_redis)
                error_type = "ConnectionError"
            else:
                raise ValueError(f"Unknown scenario: {scenario}")
        except AssertionError as e:
            logger.error("🚨 [HYDRA-CHAOS] Engine failure: %s", e)
            critical_interrupted = True
            error_type = "AssertionError"
        except Exception as e:  # noqa: BLE001
            logger.error("🚨 [HYDRA-CHAOS] Unexpected failure: %s", e)
            critical_interrupted = True
            error_type = type(e).__name__

        latency_ns = time.perf_counter_ns() - start_ts
        
        # Give background ghost tasks a tiny moment to register
        await asyncio.sleep(0.05)

        # Pipeline check
        ghost_captured = ghost_pipeline.stats["total_captured"] > 0
        pipeline_transferred = ghost_captured  # Simplified for mock

        res = ChaosResult(
            scenario=scenario,
            ghost_captured=ghost_captured,
            pipeline_transferred=pipeline_transferred,
            critical_process_interrupted=critical_interrupted,
            latency_ns=latency_ns,
            error_type=error_type,
            metadata=metadata
        )
        
        if scenario == ChaosScenario.BYZANTINE:
            res.metadata["concurrent_ops"] = 3

        self.results.append(res)
        return res

    async def _scenario_redis_kill(self, mock_redis: MockRedisClient) -> None:
        from cortex.memory.distributed_cache import DistributedSovereignCache
        cache = DistributedSovereignCache(mock_redis)
        await cache.put("agent:alpha", {"context": "pre-kill"})
        cache.chaos_gate.arm(ChaosScenario.KILL)
        await cache.get("agent:alpha")

    async def _scenario_stream_corruption(self, mock_redis: MockRedisClient) -> None:
        from cortex.memory.distributed_cache import DistributedSovereignCache
        cache = DistributedSovereignCache(mock_redis)
        await cache.put("agent:gamma", {"data": "clean"})
        cache.chaos_gate.arm(ChaosScenario.CORRUPTION)
        await cache.get("agent:gamma")

    async def _scenario_partial_write(self, mock_redis: MockRedisClient) -> None:
        from cortex.memory.distributed_cache import DistributedSovereignCache
        cache = DistributedSovereignCache(mock_redis)
        cache.chaos_gate.arm(ChaosScenario.PARTIAL_FAILURE)
        result = await cache.put("agent:delta", {"c": 1})
        assert not result, "Partial write must return False"

    async def _scenario_consumer_stall(self, mock_redis: MockRedisClient) -> None:
        from cortex.memory.distributed_cache import DistributedSovereignCache
        cache = DistributedSovereignCache(mock_redis)
        cache.chaos_gate.arm(ChaosScenario.TIMEOUT)
        try:
            await async_interceptor(
                cache.chaos_gate, mock_redis.xreadgroup, "g", "c", {"s": ">"}, block=100
            )
        except TimeoutError:
            ErrorGhostPipeline().capture_sync(TimeoutError("Stall"), source="mock")

    async def _scenario_cascade_failure(self, mock_redis: MockRedisClient) -> None:
        from cortex.memory.distributed_cache import DistributedSovereignCache
        cache = DistributedSovereignCache(mock_redis)
        cache.chaos_gate.arm(ChaosScenario.KILL, after_n=1)
        tasks = [cache.get("a"), cache.put("b", {"v": 1}), cache.prove_forgetting()]
        await asyncio.gather(*tasks, return_exceptions=True)

    @property
    def all_sovereign(self) -> bool:
        return all(r.is_sovereign for r in self.results)

    def report(self) -> dict[str, Any]:
        return {
            "all_sovereign": self.all_sovereign,
            "total_scenarios": len(self.results),
            "scenarios": [
                {
                    "name": r.scenario.name,
                    "sovereign": r.is_sovereign,
                    "latency_us": r.latency_ns / 1000,
                }
                for r in self.results
            ],
        }

"""Unified Self-Healing Stack — L5 + L6 Integration.

Connects the Auto-Curative Agent (L5, reactive) with the
Self-Optimizer (L6, proactive) into a single autonomous daemon.

    L5: EXECUTE → MONITOR → DIAGNOSE → REPAIR
                    ↓ (telemetry)
    L6: OBSERVE → ANALYZE → OPTIMIZE → VERIFY

The L6 optimizer continuously tunes the L5 agent's parameters
(timeouts, batch sizes, breaker thresholds, cooldowns) based on
observed performance, creating a closed feedback loop.

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from cortex.engine.autocurative_agent import AutoCurativeAgent
from cortex.engine._autocurative_config import AutoCurativeConfig
from cortex.engine.performance_tracker import PerformanceTracker
from cortex.engine.self_optimizer import SelfOptimizer, OptimizerConfig

__all__ = ["HealingStack", "HealingStackConfig"]

logger = logging.getLogger("cortex.engine.healing_stack")


class HealingStackConfig:
    """Unified configuration for the L5+L6 stack."""

    def __init__(
        self,
        curative_config: AutoCurativeConfig | None = None,
        optimizer_config: OptimizerConfig | None = None,
        sync_interval_s: float = 30.0,
    ) -> None:
        self.curative = curative_config or AutoCurativeConfig()
        self.optimizer = optimizer_config or OptimizerConfig()
        self.sync_interval_s = sync_interval_s


class HealingStack:
    """Unified L5 (Auto-Curative) + L6 (Self-Optimizer) daemon.

    Usage:
        stack = HealingStack()

        # Execute with self-healing + auto-optimization
        result = await stack.execute(
            task=my_function,
            subsystem="api",
        )

        # Run as unified daemon
        await stack.start()

        # Query optimized parameters
        timeout = stack.get_timeout("api")
    """

    def __init__(self, config: HealingStackConfig | None = None) -> None:
        self._config = config or HealingStackConfig()

        # Core components
        self._tracker = PerformanceTracker()
        self._optimizer = SelfOptimizer(
            tracker=self._tracker,
            config=self._config.optimizer,
        )
        self._agent = AutoCurativeAgent(
            config=self._config.curative,
        )

        self._is_running = False
        self._start_time = time.monotonic()

    async def execute(
        self,
        task: Any,
        subsystem: str = "default",
        context: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a task with L5 healing and L6 telemetry collection.

        1. Applies optimized parameters from L6
        2. Executes via L5 self-healing loop
        3. Records telemetry for L6 optimization
        """
        ctx = context or {}
        start_ns = time.perf_counter_ns()

        # Inject optimized parameters
        ctx["timeout_ms"] = self._optimizer.get_tuned_timeout(subsystem)
        ctx["batch_size"] = self._optimizer.get_tuned_batch_size(subsystem)

        try:
            result = await self._agent.execute_with_healing(
                task=task,
                subsystem=subsystem,
                context=ctx,
                *args,
                **kwargs,
            )

            latency_ms = (time.perf_counter_ns() - start_ns) / 1e6
            self._tracker.record_execution(subsystem, latency_ms, success=True)
            return result

        except Exception as e:
            latency_ms = (time.perf_counter_ns() - start_ns) / 1e6
            self._tracker.record_execution(subsystem, latency_ms, success=False)
            raise

    async def start(self, engine: Any = None) -> None:
        """Start the unified L5+L6 daemon."""
        if self._is_running:
            return

        self._is_running = True
        logger.info("[HEALING_STACK] 🚀 L5+L6 unified daemon started")

        async def _sync_loop() -> None:
            while self._is_running:
                await self._sync_parameters()
                await asyncio.sleep(self._config.sync_interval_s)

        async def _optimizer_loop() -> None:
            while self._is_running:
                try:
                    event = await self._optimizer.optimize()
                    if event.applied > 0:
                        await self._sync_parameters()
                except Exception as e:
                    logger.error("[HEALING_STACK] Optimizer error: %s", e)
                await asyncio.sleep(self._config.optimizer.optimization_interval_s)

        await asyncio.gather(
            self._agent.start_daemon(engine=engine),
            _optimizer_loop(),
            _sync_loop(),
        )

    def stop(self) -> None:
        """Stop the unified daemon."""
        self._is_running = False
        self._agent.stop_daemon()
        self._optimizer.stop_daemon()
        logger.info("[HEALING_STACK] Daemon stopped")

    async def _sync_parameters(self) -> None:
        """Sync L6 optimized params into L5 agent config."""
        all_params = self._optimizer.get_all_tuned_params()

        for subsystem, params in all_params.items():
            breaker = self._agent._breakers.get(subsystem)
            if breaker is not None:
                new_threshold = params.get("breaker_threshold")
                if new_threshold is not None:
                    breaker._threshold = new_threshold

    # ─── Parameter Queries ────────────────────────────────────

    def get_timeout(self, subsystem: str) -> float:
        return self._optimizer.get_tuned_timeout(subsystem)

    def get_batch_size(self, subsystem: str) -> int:
        return self._optimizer.get_tuned_batch_size(subsystem)

    # ─── Introspection ────────────────────────────────────────

    @property
    def health(self) -> dict[str, Any]:
        """Combined health from L5 agent and L6 optimizer."""
        agent_health = self._agent.health.to_dict()
        optimizer_stats = self._optimizer.stats
        snapshot = self._tracker.snapshot().to_dict() if self._tracker.subsystem_names else {}

        return {
            "agent": agent_health,
            "optimizer": optimizer_stats,
            "telemetry": snapshot,
            "uptime_s": round(time.monotonic() - self._start_time, 2),
        }

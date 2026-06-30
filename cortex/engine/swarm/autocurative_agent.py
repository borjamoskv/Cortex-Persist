# [C5-REAL] Exergy-Maximized
"""Auto-Curative Agent - Level 5 Self-Healing Daemon.

Unifies the CORTEX self-healing primitives into a single closed-loop daemon.

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Any

from cortex.engine.evo._autocurative_config import AutoCurativeConfig
from cortex.engine.evo._autocurative_helper import (
    execute_with_healing,
    handle_error,
    start_daemon,
)
from cortex.engine.evo._autocurative_state import AgentHealth, HealingEvent, HealingPhase
from cortex.engine.evo.repair_strategies import (
    REPAIR_REGISTRY,
)
from cortex.engine.healing.circuit_breaker import CircuitBreaker
from cortex.engine.uncategorized.endocrine import ENDOCRINE, HormoneType

__all__ = [
    "AgentHealth",
    "AutoCurativeAgent",
    "AutoCurativeConfig",
    "HealingEvent",
]

logger = logging.getLogger("cortex.engine.autocurative")


class AutoCurativeAgent:
    """Level 5 Self-Healing Daemon."""

    def __init__(
        self,
        config: AutoCurativeConfig | None = None,
        repair_registry: Any | None = None,
    ) -> None:
        self.config = config or AutoCurativeConfig()
        self._registry = repair_registry or REPAIR_REGISTRY
        self._phase = HealingPhase.IDLE
        self._start_time = time.monotonic()
        self._is_running = False
        self._daemon_task = None

        # Metrics
        self._total_errors = 0
        self._total_repairs = 0
        self._successful_repairs = 0
        self._event_history = deque(maxlen=self.config.max_event_history)

        # Circuit breakers per subsystem
        self._breakers = {}

        # Concurrency control
        self._repair_semaphore = asyncio.Semaphore(self.config.max_concurrent_repairs)

        # Rust engine (optional fast-path)
        self._rust_engine = None
        self._try_init_rust_engine()

    def _try_init_rust_engine(self) -> None:
        """Attempt to load the Rust AutoCurativeEngine for fast-path diagnosis."""
        try:
            from cortex_rs import AutoCurativeEngine  # type: ignore[import-untyped]

            self._rust_engine = AutoCurativeEngine(window_size=1000)
            logger.info("[AUTOCURATIVE] Rust fast-path engine loaded")
        except ImportError:
            logger.debug("[AUTOCURATIVE] Rust engine not available - using Python fallback")

    def _get_or_create_breaker(self, subsystem: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a subsystem."""
        if subsystem not in self._breakers:
            self._breakers[subsystem] = CircuitBreaker(
                name=f"autocurative:{subsystem}",
                failure_threshold=self.config.breaker_failure_threshold,
                recovery_timeout=self.config.breaker_recovery_timeout_s,
            )
        return self._breakers[subsystem]

    async def execute_with_healing(
        self,
        task: Any,
        subsystem: str = "default",
        context: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a task with the full self-healing loop."""
        return await execute_with_healing(self, task, subsystem, context, *args, **kwargs)

    async def handle_error(
        self,
        error: Exception,
        subsystem: str,
        context: dict[str, Any] | None = None,
    ) -> HealingEvent | None:
        """Handle a single error through the diagnosis → repair pipeline."""
        return await handle_error(self, error, subsystem, context)

    async def start_daemon(
        self,
        engine: Any = None,
        project: str = "autocurative",
    ) -> None:
        """Start the self-healing daemon loop."""
        await start_daemon(self, engine, project)

    def stop_daemon(self) -> None:
        """Stop the self-healing daemon."""
        self._is_running = False
        self._phase = HealingPhase.IDLE
        if self._daemon_task and not self._daemon_task.done():
            self._daemon_task.cancel()
        logger.info("[AUTOCURATIVE] Daemon stopped")

    @property
    def phase(self) -> HealingPhase:
        """Current phase of the self-healing loop."""
        return self._phase

    @property
    def health(self) -> AgentHealth:
        """Get the current health state of the agent."""
        uptime = time.monotonic() - self._start_time
        cortisol = ENDOCRINE.get_level(HormoneType.CORTISOL)

        # Health score
        if self._total_repairs > 0:
            repair_rate = self._successful_repairs / self._total_repairs
        else:
            repair_rate = 1.0

        recent_errors = sum(1 for e in self._event_history if e.severity > 0.7)
        health_score = max(0, min(100, 100 - recent_errors * 10)) * repair_rate

        # Status
        if health_score < self.config.health_score_critical:
            status = "critical"
        elif cortisol > self.config.cortisol_alarm_threshold:
            status = "degraded"
        elif self._phase == HealingPhase.REPAIRING:
            status = "healing"
        else:
            status = "healthy"

        return AgentHealth(
            status=status,
            uptime_s=uptime,
            total_errors_detected=self._total_errors,
            total_repairs_attempted=self._total_repairs,
            total_repairs_succeeded=self._successful_repairs,
            active_circuit_breakers={
                name: breaker.state.name for name, breaker in self._breakers.items()
            },
            cortisol_level=cortisol,
            health_score=health_score,
            recent_events=[e.to_dict() for e in list(self._event_history)[-10:]],
        )

    def get_healing_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent healing events."""
        events = list(self._event_history)
        return [e.to_dict() for e in events[-limit:]]

    def get_rust_metrics(self) -> dict[str, Any] | None:
        """Get metrics from the Rust fast-path engine."""
        if self._rust_engine is None:
            return None
        return dict(self._rust_engine.get_metrics())  # pyright: ignore[reportAttributeAccessIssue]

    def reset_breaker(self, subsystem: str) -> bool:
        """Manually reset a circuit breaker."""
        breaker = self._breakers.get(subsystem)
        if breaker is not None:
            breaker.reset()
            return True
        return False

    def reset_all_breakers(self) -> int:
        """Reset all circuit breakers. Returns count reset."""
        count = 0
        for breaker in self._breakers.values():
            breaker.reset()
            count += 1
        return count

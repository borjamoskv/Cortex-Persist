"""circuit_breaker.py

A lightweight circuit‑breaker implementation used by the Compaction Monitor
sidecar to protect calls to the external ``cortex.compactor.compact`` service.
It follows the classic Closed → Open → Half‑Open state machine with configurable
error thresholds and cooldown periods.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

LOGGER = logging.getLogger(__name__)


class CircuitBreaker:
    """Simple async circuit breaker.

    Parameters
    ----------
    failure_threshold: int
        Number of consecutive failures before opening the circuit.
    recovery_timeout: float
        Seconds to wait in the Open state before transitioning to Half‑Open.
    half_open_success_threshold: int
        Number of successful calls required in Half‑Open to close the circuit.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        half_open_success_threshold: int = 2,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_success_threshold = half_open_success_threshold
        self._state = "CLOSED"
        self._failure_count = 0
        self._success_count = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> str:
        return self._state

    async def call(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """Execute ``func`` respecting the circuit‑breaker state.

        If the circuit is Open and the timeout has not elapsed, a ``RuntimeError``
        is raised immediately. In Half‑Open the call is allowed but the outcome
        influences state transition.
        """
        if self._state == "OPEN":
            if self._opened_at is None:
                # Should never happen, but guard against None
                self._opened_at = time.time()
            elapsed = time.time() - self._opened_at
            if elapsed < self.recovery_timeout:
                raise RuntimeError("Circuit breaker is OPEN; request blocked")
            # Timeout elapsed – move to HALF‑OPEN
            self._state = "HALF_OPEN"
            self._success_count = 0
            LOGGER.info("Circuit breaker transitioning to HALF_OPEN after timeout")

        try:
            result = await func(*args, **kwargs)
        except Exception as exc:
            await self._record_failure(exc)
            raise
        else:
            await self._record_success()
            return result

    async def _record_failure(self, exc: Exception) -> None:
        self._failure_count += 1
        LOGGER.warning(
            "Circuit breaker failure %d/%d: %s",
            self._failure_count,
            self.failure_threshold,
            exc,
        )
        if self._state == "HALF_OPEN" or self._failure_count >= self.failure_threshold:
            self._state = "OPEN"
            self._opened_at = time.time()
            LOGGER.error("Circuit breaker OPENed due to failures")
        # Reset success counter in case we were HALF_OPEN
        self._success_count = 0

    async def _record_success(self) -> None:
        if self._state == "HALF_OPEN":
            self._success_count += 1
            if self._success_count >= self.half_open_success_threshold:
                self._state = "CLOSED"
                self._failure_count = 0
                self._success_count = 0
                self._opened_at = None
                LOGGER.info("Circuit breaker CLOSED after successful half‑open trials")
        else:
            # In CLOSED state just reset failure count on success
            self._failure_count = 0


# Global instance used by the sidecar runner
circuit_breaker = CircuitBreaker()


async def call_external_compact() -> None:
    """Placeholder for the external compaction service.

    In a real deployment this would perform an HTTP request or RPC call to
    ``cortex.compactor.compact``. Here we simulate a call that may fail
    randomly to demonstrate the breaker.
    """

    async def dummy_call():
        # Simulate occasional failure
        import random

        await asyncio.sleep(0.1)
        if random.random() < 0.2:
            raise RuntimeError("Simulated external compaction failure")
        return "ok"

    await circuit_breaker.call(dummy_call)

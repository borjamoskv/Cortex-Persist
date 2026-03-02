"""
CORTEX v5.3 — Circuit Breaker Pattern.

Protects the system from cascading failures when a subsystem
(e.g., Ledger integrity verification) fails repeatedly.

Derivation: Ω₅ (Antifragile by Default) — failures trigger degraded mode, not system death.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from enum import Enum, auto
from typing import Any, TypeVar

__all__ = ["CircuitBreaker", "CircuitState"]

logger = logging.getLogger("cortex.circuit_breaker")

T = TypeVar("T")


class CircuitState(Enum):
    """Three-state circuit breaker following the standard pattern."""

    CLOSED = auto()  # Normal operation — all calls go through
    OPEN = auto()  # Failing — reject calls immediately
    HALF_OPEN = auto()  # Testing recovery — allow one probe call


class CircuitBreaker:
    """Async-aware circuit breaker for CORTEX subsystems.

    Usage:
        breaker = CircuitBreaker("ledger", failure_threshold=5, recovery_timeout=30.0)

        try:
            result = await breaker.call(verify_integrity_async)
        except RuntimeError:
            # Circuit is open — system in degraded mode
            pass

    State transitions:
        CLOSED → (N failures) → OPEN
        OPEN   → (timeout elapsed) → HALF_OPEN
        HALF_OPEN → (success) → CLOSED
        HALF_OPEN → (failure) → OPEN
    """

    __slots__ = (
        "_name",
        "_state",
        "_failures",
        "_last_failure_time",
        "_threshold",
        "_timeout",
        "_total_trips",
    )

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> None:
        self._name = name
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._last_failure_time: float | None = None
        self._threshold = failure_threshold
        self._timeout = recovery_timeout
        self._total_trips = 0

    @property
    def state(self) -> CircuitState:
        """Current circuit state (may auto-transition OPEN → HALF_OPEN)."""
        if self._state == CircuitState.OPEN and self._last_failure_time is not None:
            if time.monotonic() - self._last_failure_time > self._timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit '%s' → HALF_OPEN (probing recovery)", self._name)
        return self._state

    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED

    @property
    def total_trips(self) -> int:
        return self._total_trips

    async def call(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """Execute func through the circuit breaker.

        Raises RuntimeError if circuit is OPEN.
        """
        current = self.state

        if current == CircuitState.OPEN:
            raise RuntimeError(
                f"Circuit breaker '{self._name}' is OPEN — "
                f"subsystem unavailable (failures={self._failures})"
            )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self) -> None:
        """Reset failures on success."""
        if self._state == CircuitState.HALF_OPEN:
            logger.info("Circuit '%s' → CLOSED (recovered)", self._name)
        self._state = CircuitState.CLOSED
        self._failures = 0

    def _on_failure(self) -> None:
        """Track failure and potentially trip the breaker."""
        self._failures += 1
        self._last_failure_time = time.monotonic()

        if self._failures >= self._threshold:
            self._state = CircuitState.OPEN
            self._total_trips += 1
            logger.error(
                "Circuit '%s' → OPEN (threshold=%d reached, trip #%d). "
                "Entering degraded mode for %.1fs",
                self._name,
                self._threshold,
                self._total_trips,
                self._timeout,
            )

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._last_failure_time = None
        logger.info("Circuit '%s' manually reset", self._name)

    def to_dict(self) -> dict[str, Any]:
        """Diagnostic snapshot."""
        return {
            "name": self._name,
            "state": self.state.name,
            "failures": self._failures,
            "threshold": self._threshold,
            "total_trips": self._total_trips,
            "recovery_timeout": self._timeout,
        }

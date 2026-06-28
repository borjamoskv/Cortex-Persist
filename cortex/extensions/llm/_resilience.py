# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.
from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerError(httpx.ConnectError):
    """Raised when the circuit breaker is open or half-open and probing."""


class CircuitBreaker:
    """Circuit breaker to track provider failures and fail fast.

    Tracks consecutive failures per provider.
    After 5 consecutive failures -> open circuit (fail-fast for 60s).
    After cooldown -> half-open (allow 1 probe request).
    On probe success -> close circuit.
    """

    def __init__(self, provider_name: str, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.provider_name = provider_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = CircuitState.CLOSED
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if time.monotonic() - self.last_failure_time > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info(
                        "Circuit Breaker [%s] [HALF-OPEN] -> Probing provider...",
                        self.provider_name,
                    )
                else:
                    raise CircuitBreakerError(f"Circuit breaker for {self.provider_name} is OPEN")
            elif self.state == CircuitState.HALF_OPEN:
                raise CircuitBreakerError(
                    f"Circuit breaker for {self.provider_name} is HALF-OPEN (probing)"
                )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            async with self._lock:
                if self.state == CircuitState.HALF_OPEN:
                    logger.info(
                        "Circuit Breaker [%s] [CLOSED] -> Recovery successful.", self.provider_name
                    )
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        else:
            if self.is_countable_failure(exc_val):
                async with self._lock:
                    self.failure_count += 1
                    self.last_failure_time = time.monotonic()
                    if (
                        self.state == CircuitState.HALF_OPEN
                        or self.failure_count >= self.failure_threshold
                    ):
                        if self.state != CircuitState.OPEN:
                            self.state = CircuitState.OPEN
                            logger.warning(
                                "Circuit Breaker [%s] [OPEN] -> Threshold reached (%d failures)",
                                self.provider_name,
                                self.failure_count,
                            )

    @staticmethod
    def is_countable_failure(exc: Any) -> bool:
        """Determines if an exception should count towards the circuit breaker threshold."""
        if isinstance(
            exc,
            (
                httpx.NetworkError,
                httpx.TimeoutException,
                httpx.RemoteProtocolError,
                httpx.DecodingError,
                UnicodeDecodeError,
            ),
        ):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            return status == 429 or status >= 500
        return False


def is_retryable(exc: Any) -> bool:
    """Returns True if the exception is a transient error that should be retried."""
    if isinstance(exc, CircuitBreakerError):
        return False
    return CircuitBreaker.is_countable_failure(exc)


async def resilient_call(
    func: Callable[[], Any],
    provider_name: str,
    circuit_breaker: CircuitBreaker,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
) -> Any:
    """Executes a function with retry and circuit breaker logic."""
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        start_time = time.monotonic()
        try:
            async with circuit_breaker:
                result = await func()
                latency = time.monotonic() - start_time
                logger.info(
                    "LLM Call [OK] -> Provider: %s | Latency: %.2fs | Attempt: %d",
                    provider_name,
                    latency,
                    attempt,
                )
                return result
        except Exception as e:
            latency = time.monotonic() - start_time
            last_exc = e

            # Fail-fast if circuit breaker is active
            if isinstance(e, CircuitBreakerError):
                logger.error("LLM Call [CIRCUIT-OPEN] -> Provider: %s", provider_name)
                raise

            # Non-retryable errors (FATAL or FAIL-FAST)
            if isinstance(e, httpx.HTTPStatusError) and e.response.status_code in (
                400,
                401,
                403,
                429,
            ):
                logger.error(
                    "LLM Call [FATAL/FAIL-FAST] -> Provider: %s | Status: %d | Latency: %.2fs",
                    provider_name,
                    e.response.status_code,
                    latency,
                )
                raise

            if not is_retryable(e) or attempt == max_attempts:
                status = getattr(getattr(e, "response", None), "status_code", "ERROR")
                logger.error(
                    "LLM Call [FAIL] -> Provider: %s | Status: %s | Latency: %.2fs | Attempt: %d/%d",
                    provider_name,
                    status,
                    latency,
                    attempt,
                    max_attempts,
                )
                raise

            # Exponential backoff with jitter
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            jitter = delay * 0.1 * random.uniform(-1, 1)
            sleep_s = delay + jitter

            logger.warning(
                "LLM Call [RETRY] -> Provider: %s | Error: %s | Next try in %.2fs (Attempt %d/%d)",
                provider_name,
                type(e).__name__,
                sleep_s,
                attempt,
                max_attempts,
            )
            await asyncio.sleep(sleep_s)

    if last_exc:
        raise last_exc
    raise RuntimeError("Unreachable")

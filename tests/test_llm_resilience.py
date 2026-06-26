# [C5-REAL] Exergy-Maximized
import asyncio
import time
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from cortex_extensions.llm._resilience import (
    CircuitBreaker,
    CircuitState,
    resilient_call,
    CircuitBreakerError,
)


@pytest.mark.asyncio
async def test_retry_exponential_backoff():
    mock_func = AsyncMock()
    # Fail twice, then succeed
    mock_func.side_effect = [
        httpx.HTTPStatusError(
            "Retryable", request=MagicMock(), response=MagicMock(status_code=500)
        ),
        httpx.HTTPStatusError(
            "Retryable", request=MagicMock(), response=MagicMock(status_code=503)
        ),
        "Success",
    ]

    cb = CircuitBreaker("test-provider")

    start_time = time.monotonic()
    # Using small base_delay for tests
    result = await resilient_call(mock_func, "test-provider", cb, max_attempts=3, base_delay=0.1)
    end_time = time.monotonic()

    assert result == "Success"
    assert mock_func.call_count == 3
    # First delay ~0.1s, second delay ~0.2s. Total >= 0.25s (allowing for slight timing variations)
    assert end_time - start_time >= 0.25


@pytest.mark.asyncio
async def test_non_retryable_errors_fail_immediately():
    mock_func = AsyncMock()
    mock_func.side_effect = httpx.HTTPStatusError(
        "Fatal", request=MagicMock(), response=MagicMock(status_code=401)
    )

    cb = CircuitBreaker("test-provider")

    with pytest.raises(httpx.HTTPStatusError) as excinfo:
        await resilient_call(mock_func, "test-provider", cb, max_attempts=3, base_delay=0.1)

    assert excinfo.value.response.status_code == 401
    assert mock_func.call_count == 1


@pytest.mark.asyncio
async def test_circuit_breaker_transitions():
    cb = CircuitBreaker("test-provider", failure_threshold=2, recovery_timeout=1)

    # CLOSED state
    assert cb.state == CircuitState.CLOSED

    async def fail():
        raise httpx.HTTPStatusError(
            "Fail", request=MagicMock(), response=MagicMock(status_code=500)
        )

    # First failure
    with pytest.raises(httpx.HTTPStatusError):
        await resilient_call(fail, "test-provider", cb, max_attempts=1)
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 1

    # Second failure -> OPEN
    with pytest.raises(httpx.HTTPStatusError):
        await resilient_call(fail, "test-provider", cb, max_attempts=1)
    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 2

    # Immediate fail when OPEN (Fail-fast check)
    with pytest.raises(CircuitBreakerError) as excinfo:
        async with cb:
            pass
    assert "OPEN" in str(excinfo.value)

    # Fail-fast check with resilient_call (should NOT retry)
    mock_func = AsyncMock()
    with pytest.raises(CircuitBreakerError):
        await resilient_call(mock_func, "test-provider", cb, max_attempts=3)
    assert mock_func.call_count == 0

    # Wait for recovery timeout
    await asyncio.sleep(1.1)

    # HALF-OPEN on next call
    mock_success = AsyncMock(return_value="OK")
    result = await resilient_call(mock_success, "test-provider", cb, max_attempts=1)

    assert result == "OK"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_failure():
    cb = CircuitBreaker("test-provider", failure_threshold=2, recovery_timeout=1)

    # Force OPEN
    cb.state = CircuitState.OPEN
    cb.failure_count = 2
    cb.last_failure_time = time.monotonic() - 2  # already timed out

    # Probe fails -> OPEN again
    async def fail():
        raise httpx.HTTPStatusError(
            "Fail", request=MagicMock(), response=MagicMock(status_code=500)
        )

    with pytest.raises(httpx.HTTPStatusError):
        await resilient_call(fail, "test-provider", cb, max_attempts=1)

    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 3


@pytest.mark.asyncio
async def test_concurrent_circuit_breaker_access():
    cb = CircuitBreaker("test-provider", failure_threshold=5, recovery_timeout=60)

    # Simulate many concurrent requests
    async def task():
        async with cb:
            await asyncio.sleep(0.01)
            return True

    results = await asyncio.gather(*(task() for _ in range(10)))
    assert all(results)
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_concurrent_probe_limitation():
    cb = CircuitBreaker("test-provider", failure_threshold=1, recovery_timeout=0.1)

    # OPEN it
    cb.state = CircuitState.OPEN
    cb.last_failure_time = time.monotonic()

    await asyncio.sleep(0.2)

    # Now it should be able to enter HALF-OPEN.
    # But only one should be allowed.

    async def probe_task(id):
        try:
            async with cb:
                await asyncio.sleep(0.2)  # hold it in HALF-OPEN
                return f"OK-{id}"
        except CircuitBreakerError:
            return "BLOCKED"

    results = await asyncio.gather(*(probe_task(i) for i in range(5)))

    assert results.count("BLOCKED") == 4
    # The one that didn't get blocked should have finished
    assert any(r.startswith("OK-") for r in results)

# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.
import asyncio
import json
import logging
import random
import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from cortex.extensions.llm._resilience import CircuitBreakerError, is_retryable

logger = logging.getLogger("cortex.extensions.llm")


async def process_stream_lines(response: httpx.Response) -> AsyncGenerator[str, None]:
    async for line in response.aiter_lines():
        if not line or not line.startswith("data: "):
            continue
        data_str = line[6:].strip()
        if data_str == "[DONE]":
            break
        try:
            data = json.loads(data_str)
            if delta := data.get("choices", [{}])[0].get("delta", {}).get("content"):
                yield delta
        except (json.JSONDecodeError, KeyError, IndexError):
            continue


async def execute_stream(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    circuit_breaker,
    provider_name: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> AsyncGenerator[str, None]:
    last_exc = None
    max_attempts = 3
    yielded_any = False

    for attempt in range(1, max_attempts + 1):
        start_time = time.monotonic()
        try:
            async with (
                circuit_breaker,
                semaphore,
                client.stream("POST", url, headers=headers, json=payload) as response,
            ):
                response.raise_for_status()
                latency = time.monotonic() - start_time
                logger.info(
                    "LLM Stream [CONNECTED] -> Provider: %s | Latency: %.2fs | Attempt: %d",
                    provider_name,
                    latency,
                    attempt,
                )
                async for chunk in process_stream_lines(response):
                    yield chunk
                    yielded_any = True
                return
        except Exception as e:
            latency = time.monotonic() - start_time
            last_exc = e
            if yielded_any:
                logger.error(
                    "LLM Stream [FAIL-MIDSTREAM] -> Provider: %s | Error: %s",
                    provider_name,
                    type(e).__name__,
                )
                raise
            if isinstance(e, CircuitBreakerError):
                raise
            if isinstance(e, httpx.HTTPStatusError) and e.response.status_code in (400, 401, 403):
                raise
            if not is_retryable(e) or attempt == max_attempts:
                raise
            delay = min(1.0 * (2 ** (attempt - 1)), 30.0)
            sleep_s = delay + (delay * 0.1 * random.uniform(-1, 1))
            logger.warning(
                "LLM Stream [RETRY] -> Provider: %s | Error: %s | Next try in %.2fs",
                provider_name,
                type(e).__name__,
                sleep_s,
            )
            await asyncio.sleep(sleep_s)

    if last_exc:
        raise last_exc

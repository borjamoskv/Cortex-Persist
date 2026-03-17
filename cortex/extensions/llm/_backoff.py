# This file is part of CORTEX. Apache-2.0.
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from .provider import LLMProvider

logger = logging.getLogger("cortex.extensions.llm.backoff")


def extract_retry_delay(text: str) -> float | None:
    """Extrae el delay de reintento desde el JSON o via regex."""
    try:
        data = json.loads(text)
        for detail in data.get("error", {}).get("details", []):
            meta = detail.get("metadata", {})
            delay_str = detail.get("retryDelay") or meta.get("quotaResetDelay")
            if delay_str and isinstance(delay_str, str):
                if delay_str.endswith("ms"):
                    return float(delay_str[:-2]) / 1000.0
                elif delay_str.endswith("s"):
                    return float(delay_str[:-1])
    except (KeyError, TypeError, ValueError, AttributeError):
        pass

    match = re.search(r'"(?:quotaResetDelay|retryDelay)"\s*:\s*"([0-9\.]+)(m?s)"', text)
    if match:
        try:
            val = float(match.group(1))
            return val / 1000.0 if match.group(2) == "ms" else val
        except ValueError:
            pass
    return None


async def handle_429_backoff(
    provider: LLMProvider,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    original_error: httpx.HTTPStatusError,
) -> str:
    """Maneja el backoff rápido o el fallback hipersónico."""
    # Only OpenAI gets a local retry loop due to its stability/resilience
    if provider.provider_name != "openai":
        logger.warning(
            "LLM API [429 Quota Exceeded Final] on %s. Fallback inmediato al meta-router...",
            provider.model,
        )
        raise original_error

    last_error = original_error
    for attempt in range(1, 4):
        safe_delay = (attempt * 1.5) + (1.0 * attempt)
        logger.warning(
            "LLM API [429 Quota Exceeded] on %s. Auto-sleeping for %.2fs (attempt %d/3)...",
            provider.model,
            safe_delay,
            attempt,
        )
        await asyncio.sleep(safe_delay)
        try:
            # We bypass the complex _execute_completion and go to the raw version
            # This is slightly coupled but necessary to avoid recursion or duplication
            return await provider._execute_completion_raw(url, headers, payload)
        except httpx.HTTPStatusError as e2:
            if e2.response.status_code == 429:
                last_error = e2
                continue
            raise original_error from e2
        except (httpx.HTTPError, ValueError, KeyError) as retry_e:
            logger.error("LLM Quota Retry Failure: %s", retry_e)
            raise original_error from retry_e

    return await execute_fallback(provider, payload, last_error)


async def execute_fallback(
    provider: LLMProvider, payload: dict[str, Any], original_error: httpx.HTTPStatusError
) -> str:
    """Ejecuta el fallback hacia un modelo más estable si todo falla."""
    logger.warning(
        "LLM API [429 Quota Exceeded Final] on %s. Fallback to Open Code (Qwen Coder)...",
        provider.model,
    )
    if provider.provider_name == "qwen":
        raise original_error

    from .provider import LLMProvider as LLMProviderSub

    fallback_provider = LLMProviderSub(provider="qwen")
    try:
        fb_url, fb_headers = fallback_provider._prepare_request()
        fb_payload = {
            "model": fallback_provider.model,
            "messages": payload.get("messages", []),
            "temperature": payload.get("temperature", 0.3),
            "max_tokens": payload.get("max_tokens", 2048),
        }
        return await fallback_provider._execute_completion_raw(fb_url, fb_headers, fb_payload)
    except (httpx.HTTPError, ValueError, KeyError) as fallback_e:
        logger.error("LLM Fallback Failure: %s", fallback_e)
        raise original_error from fallback_e
    finally:
        await fallback_provider.close()

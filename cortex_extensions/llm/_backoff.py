# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from .provider import LLMProvider

logger = logging.getLogger("cortex_extensions.llm.backoff")


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
                if delay_str.endswith("s"):
                    return float(delay_str[:-1])
    except Exception as exc:
        logger.warning("Suppressed exception: %s", exc)

    match = re.search(r'"(?:quotaResetDelay|retryDelay)"\s*:\s*"([0-9\.]+)(m?s)"', text)
    if match:
        try:
            val = float(match.group(1))
            return val / 1000.0 if match.group(2) == "ms" else val
        except Exception as exc:
            logger.warning("Suppressed exception: %s", exc)
    return None


async def handle_429_backoff(
    provider: LLMProvider,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    original_error: httpx.HTTPStatusError,
) -> str:
    """Maneja el backoff rápido o el fallback hipersónico."""
    # ── Protocolo PULMONES Upgrade ──
    # Extraer wait time desde el error (Gemini/OpenAI)
    wait_time = extract_retry_delay(original_error.response.text)

    # Si el wait_time es muy alto (>60s), fallamos inmediato para no bloquear el enjambre
    if wait_time and wait_time > 60.0:
        logger.warning(
            "LLM API [429 Quota Exhausted] on %s. Reset delay too high (%.1fs). Falling back.",
            provider.model_name,
            wait_time,
        )
        return await execute_fallback(provider, payload, original_error)

    # ── Re-Inyección con Backoff Dinámico ──
    last_error = original_error
    max_attempts = 0 if os.environ.get("CORTEX_TESTING") == "1" else 5

    for attempt in range(1, max_attempts + 1):
        # Usar el delay del API + jitter, o un backoff exponencial base
        if wait_time:
            sleep_s = wait_time + (0.5 * attempt)
            wait_time = None  # Consumido
        else:
            sleep_s = (attempt * 2.5) + random.uniform(0.1, 1.0)

        logger.warning(
            "LLM API [429 Quota] on %s. Auto-sleeping %.2fs (attempt %d/%d)...",
            provider.model_name,
            sleep_s,
            attempt,
            max_attempts,
        )
        await asyncio.sleep(sleep_s)

        try:
            # Reintentamos la ejecución raw para bypass del quota manager local
            return await provider._execute_completion_raw(url, headers, payload)
        except httpx.HTTPStatusError as e2:
            if e2.response.status_code == 429:
                last_error = e2
                # Actualizar wait_time si el API devuelve uno nuevo
                wait_time = extract_retry_delay(e2.response.text)
                continue
            raise original_error from e2
        except (httpx.HTTPError, ValueError, KeyError) as retry_e:
            logger.error("LLM Quota Retry Failure: %s", retry_e)
            raise original_error from retry_e

    return await execute_fallback(provider, payload, last_error)


async def execute_fallback(
    provider: LLMProvider, payload: dict[str, Any], original_error: httpx.HTTPStatusError
) -> str:
    """Ejecuta el fallback hacia un modelo más estable si los intentos fallan."""
    logger.warning(
        "LLM API [429 Quota Exceeded Final] on %s. Fallback to Open Code (Qwen Coder)...",
        provider.model_name,
    )
    if provider.provider_name == "qwen":
        raise original_error

    from .provider import LLMProvider as LLMProviderSub

    fallback_provider = LLMProviderSub(provider="qwen")
    try:
        fb_url, fb_headers = fallback_provider._prepare_request()
        fb_payload = {
            "model": fallback_provider.model_name,
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

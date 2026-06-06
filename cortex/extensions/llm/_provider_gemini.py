# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.
import asyncio
import logging

import httpx

from cortex.extensions.llm._resilience import resilient_call
from cortex.extensions.llm._stealth import apply_causal_jitter, sanitize_response

logger = logging.getLogger("cortex.extensions.llm")


async def execute_gemini_native(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    circuit_breaker,
    provider_name: str,
    api_key: str,
    prompt: str,
    model_name: str,
    remote_cache: str,
    temperature: float,
    max_tokens: int,
) -> str:
    async def _call():
        model_stripped = model_name.replace("models/", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_stripped}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "cachedContent": remote_cache,
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        await apply_causal_jitter(tokens_estimate=50)
        async with semaphore:
            response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        raw_content = data["candidates"][0]["content"]["parts"][0]["text"]
        return sanitize_response(raw_content)

    try:
        return await resilient_call(_call, provider_name, circuit_breaker)
    except httpx.HTTPStatusError as e:
        logger.error("Native Gemini API Failure: %s", e.response.text[:500])
        raise ValueError(f"HTTP {e.response.status_code} from native Gemini") from e

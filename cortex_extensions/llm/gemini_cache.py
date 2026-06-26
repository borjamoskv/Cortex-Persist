# [C5-REAL] Exergy-Maximized
"""
Gemini Context Caching Gateway (AX-042).
Maneja la creación y resolución asíncrona de `cachedContents` nativo vía REST v1beta.
Las llamadas OpenAI-compatibles no soportan caching, por lo que requerimos fallback nativo.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger("cortex_extensions.llm.gemini_cache")

# The minimum required tokens to be eligible for caching in Gemini v1.5 API
GEMINI_CACHE_MIN_TOKENS: int = 32768


class GeminiCacheGateway:
    """Gateway for the Native Gemini Context Caching API."""

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._base_url = "https://generativelanguage.googleapis.com/v1beta"

        # Local state mapping of our cryptographic isolated cache_key -> Gemini remote name
        # Ex: "123abc456..." -> "cachedContents/uuid-yyy-zzz"
        self._local_to_remote: dict[str, str] = {}

    async def get_or_create_cache(
        self,
        cache_key: str,
        system_prompt: str,
        model: str,
        ttl_seconds: int = 3600,
    ) -> str | None:
        """
        Devuelve el URI remoto temporal de Gemini ('cachedContents/uuid'), creándolo si no existe.
        Si la carga es demasiado pequeña o la API falla, devuelve None para hacer fallback a Inferencia Normal.
        """
        if cache_key in self._local_to_remote:
            # We assume it's still alive without querying to save network latency.
            # A robust system would handle 404s gracefully on inference and evict the cache.
            return self._local_to_remote[cache_key]

        # Rough token estimation (1 token approx 4 chars). Minimum required is 32,768 tokens
        # We will attempt creation regardless if close, but we can fast-fail if clearly too small.
        # But for safety in multi-agent generic environments, we just try to create it.
        # Note: Gemini 1.5 Pro requires 32,768 minimum tokens to cache.
        # CORTEX typically injects massive context in the system prompt.
        if len(system_prompt) < (GEMINI_CACHE_MIN_TOKENS * 3):
            logger.debug("Gemini cache bypass: System prompt too small (<32k approx)")
            # In local dev/small tests, caching will naturally fail on Gemini side if below 32k.
            # We skip creating the cache silently and fallback to standard inference.
            return None

        url = f"{self._base_url}/cachedContents?key={self._api_key}"
        payload = {
            "model": f"models/{model}",
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "ttl": f"{ttl_seconds}s",
            # We can label it with our cache_key prefix for management purposes.
            "displayName": f"cortex-{cache_key[:8]}",
        }

        async with httpx.AsyncClient() as client:
            # Try to create
            try:
                response = await client.post(
                    url, json=payload, headers={"Content-Type": "application/json"}
                )

                if response.status_code == 400 and "too few tokens" in response.text.lower():
                    logger.debug("Gemini cache creation skipped: Too few tokens for caching block")
                    return None

                response.raise_for_status()
                data = response.json()
                remote_name = data.get("name")
                if remote_name:
                    logger.info(
                        "Gemini Remote Cache Created: %s (TTL: %s)", remote_name, ttl_seconds
                    )
                    self._local_to_remote[cache_key] = remote_name
                    return remote_name

            except httpx.HTTPStatusError as e:
                logger.warning(
                    "Gemini cache creation failed: %s %s",
                    e.response.status_code,
                    e.response.text[:200],
                )
                # Fallback to None (standard inference will take over)
            except Exception as e:
                logger.warning("Gemini cache HTTP execution error: %s", e)

        return None


_GEMINI_GATEWAYS: dict[str, GeminiCacheGateway] = {}


def get_gemini_gateway(api_key: str) -> GeminiCacheGateway:
    """True singleton provider for GeminiCacheGateway per API Key."""
    if api_key not in _GEMINI_GATEWAYS:
        _GEMINI_GATEWAYS[api_key] = GeminiCacheGateway(api_key)
    return _GEMINI_GATEWAYS[api_key]

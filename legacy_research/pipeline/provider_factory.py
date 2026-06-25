# [C5-REAL] Exergy-Maximized
"""CORTEX Pipeline - Provider Factory.

Builds the LLM execution stack for the AgentExecutor by
auto-discovering configured providers from environment variables.

Returns (CortexLLMRouter | None, BaseProvider | None) tuple.
Graceful degradation: no keys → (None, None) → executor falls back to stub.

∴ Reality: C5-REAL (env-var discovery, real provider construction)
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger("cortex.pipeline.provider_factory")

# Provider priority order: frontier-first, cost-optimized
_PROVIDER_PRIORITY: list[str] = [
    "gemini",  # Free tier available, 1M context
    "anthropic",  # Frontier reasoning
    "openai",  # Frontier general
    "deepseek",  # Cost-effective frontier
    "qwen",  # Frontier, strong code
    "openrouter",  # Meta-router fallback
    "groq",  # Fast inference
    "ollama",  # Local fallback (no key needed)
]


def build_executor_stack() -> tuple[Any | None, Any | None]:
    """Discover configured LLM providers and build execution stack.

    Returns:
        (router, fallback_provider) tuple. Both None if no providers available.
    """
    available = _discover_providers()

    if not available:
        logger.info("[FACTORY] No LLM providers configured - executor will use stub mode")
        return None, None

    logger.info(
        "[FACTORY] Discovered %d providers: %s",
        len(available),
        [p.provider_name for p in available],
    )

    # Build router if 2+ providers available
    router = _build_router(available) if len(available) >= 2 else None

    # Primary provider = first in priority order
    primary = available[0]

    return router, primary


def _discover_providers() -> list[Any]:
    """Scan environment for configured LLM providers.

    Returns providers in priority order, skipping those without API keys.
    """
    providers: list[Any] = []

    for name in _PROVIDER_PRIORITY:
        provider = _try_build_provider(name)
        if provider is not None:
            providers.append(provider)

    return providers


def _try_build_provider(name: str) -> Any | None:
    """Attempt to construct a single LLMProvider.

    Returns None if the provider cannot be initialized (missing key, import error, etc.)
    """
    try:
        from legacy_research.extensions.llm._presets import get_preset_info
        from legacy_research.extensions.llm.provider import LLMProvider

        preset = get_preset_info(name)
        if preset is None:
            return None

        env_key = preset.get("env_key") or preset.get("api_key_env", "")
        is_local = name in ("ollama", "lmstudio", "llamacpp", "vllm", "jan")

        # Local providers don't need API keys
        if is_local:
            # Only include if the service is likely running
            if not _check_local_provider(name, preset):
                return None
            return LLMProvider(provider=name)

        # Cloud providers need an API key
        if not env_key or not os.environ.get(env_key):
            return None

        return LLMProvider(provider=name)

    except Exception as e:
        logger.debug("[FACTORY] Provider '%s' unavailable: %s", name, e)
        return None


def _check_local_provider(name: str, preset: dict[str, Any]) -> bool:
    """Quick check if a local provider is reachable (non-blocking)."""
    import socket

    base_url = preset.get("base_url", "")
    if not base_url:
        return False

    try:
        # Extract host:port from base_url
        from urllib.parse import urlparse

        parsed = urlparse(base_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 11434  # Default ollama port

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _build_router(providers: list[Any]) -> Any | None:
    """Construct a CortexLLMRouter from discovered providers."""
    try:
        from legacy_research.extensions.llm.router import CortexLLMRouter

        primary = providers[0]
        fallbacks = providers[1:]

        router = CortexLLMRouter(
            primary=primary,
            fallbacks=fallbacks,
        )

        logger.info(
            "[FACTORY] Router built: primary=%s, fallbacks=%s",
            primary.provider_name,
            [p.provider_name for p in fallbacks],
        )
        return router

    except Exception as e:
        logger.warning("[FACTORY] Router construction failed: %s", e)
        return None

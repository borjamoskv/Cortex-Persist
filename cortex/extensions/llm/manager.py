# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.0 — LLM Manager.

Lazy-loading singleton for LLM providers. Mirrors the pattern
from EmbeddingManager. Gracefully degrades when no LLM is configured.

    CORTEX_LLM_PROVIDER=""          → No LLM (default)
    CORTEX_LLM_PROVIDER=qwen        → Qwen via DashScope
    CORTEX_LLM_PROVIDER=openrouter  → Any model via OpenRouter
    CORTEX_LLM_PROVIDER=ollama      → Local Ollama
    CORTEX_LLM_PROVIDER=ernie       → Baidu ERNIE 5.0 (AIMLAPI)
    CORTEX_LLM_PROVIDER=custom      → Any endpoint via CORTEX_LLM_BASE_URL
    ... and 20+ more presets
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from cortex.extensions.llm.router import CortexLLMRouter, IntentProfile

__all__ = ["LLMManager"]

logger = logging.getLogger("cortex.extensions.llm.manager")


class LLMManager:
    """Manages the LLM provider lifecycle.

    Returns None if no provider is configured — CORTEX
    continues to work without LLM (search-only mode).
    """

    def __init__(self):
        self._provider = None
        self._provider_name = os.environ.get("CORTEX_LLM_PROVIDER", "").strip()
        self._initialized = False

    def _get_provider(self):
        """Lazy-load the LLM provider."""
        if self._initialized:
            return self._provider

        self._initialized = True

        if not self._provider_name:
            logger.info("No LLM provider configured (CORTEX_LLM_PROVIDER is empty)")
            return None

        try:
            from cortex.extensions.llm.provider import LLMProvider

            self._provider = LLMProvider(provider=self._provider_name)
            logger.info("LLM provider loaded: %s", self._provider)
        except (OSError, RuntimeError, ValueError) as e:
            logger.error(
                "Failed to initialize LLM provider '%s': %s",
                self._provider_name,
                e,
            )
            self._provider = None

        return self._provider

    @property
    def available(self) -> bool:
        """True if an LLM provider is configured and loaded."""
        return self._get_provider() is not None

    @property
    def provider(self):
        """Get the LLM provider instance (or None)."""
        return self._get_provider()

    @property
    def provider_name(self) -> str:
        """Return the configured provider name (may be empty)."""
        return self._provider_name

    async def complete(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        temperature: float = 0.3,
        max_tokens: int = 2048,
        intent: IntentProfile = IntentProfile.GENERAL,
    ) -> Optional[str]:
        """Complete via the active provider through CortexLLMRouter.

        G5: Routes through execute_resilient — gains cascade, hedging,
        pool weighting, Shannon compression, and telemetry.
        """
        p = self._get_provider()
        if p is None:
            return None

        from cortex.extensions.llm._models import CortexPrompt

        cortex_prompt = CortexPrompt(
            system_instruction=system,
            working_memory=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            intent=intent,
        )
        router = CortexLLMRouter(primary=p)
        result = await router.execute_resilient(cortex_prompt)
        if result.is_ok():
            return result.value  # type: ignore[union-attr]
        logger.warning(  # type: ignore[union-attr]
            "LLMManager.complete: router exhausted cascade: %s", result.error
        )
        return None

    async def stream(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        temperature: float = 0.3,
        max_tokens: int = 2048,
        intent: IntentProfile = IntentProfile.GENERAL,
    ):
        """Stream via the active provider. Yields text chunks."""
        p = self._get_provider()
        if p is None:
            return
        async for chunk in p.stream(
            prompt=prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            intent=intent,
        ):
            yield chunk

    async def close(self) -> None:
        """Shut down the provider client."""
        if self._provider is not None:
            await self._provider.close()

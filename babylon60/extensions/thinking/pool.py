# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Provider Pool & History Tracking.

Reusable infrastructure for the thinking orchestrator:
LLM provider pool and history tracking.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from babylon60.extensions.llm.provider import LLMProvider

__all__ = [
    "ProviderPool",
    "ThinkingRecord",
]

logger = logging.getLogger("cortex_extensions.thinking.pool")


# ─── Provider Pool ───────────────────────────────────────────────────


class ProviderPool:
    """Pool of reusable LLMProviders.

    Avoids creating/destroying httpx.AsyncClient on each query.
    One provider per key (provider_name, model).
    """

    def __init__(self) -> None:
        self._pool: dict[tuple[str, str], LLMProvider] = {}

    def get(self, provider_name: str, model: str) -> LLMProvider:
        """Gets or creates a provider from the pool."""
        key = (provider_name, model)
        if key not in self._pool:
            self._pool[key] = LLMProvider(provider=provider_name, model=model)
            logger.debug("Pool: created %s:%s", provider_name, model)
        return self._pool[key]

    async def close_all(self) -> None:
        """Closes all providers in the pool."""
        for key, provider in self._pool.items():
            try:
                await provider.close()
            except (OSError, ValueError, KeyError) as e:
                logger.debug("Pool: error closing %s: %s", key, e)
        self._pool.clear()

    @property
    def size(self) -> int:
        return len(self._pool)


# ─── History Tracking ────────────────────────────────────────────────


@dataclass
class ThinkingRecord:
    """Record of a thought for retrospective analysis."""

    mode: str
    strategy: str
    models_queried: int
    models_succeeded: int
    total_latency_ms: float
    confidence: float
    agreement: float
    winner: str | None = None
    timestamp: float = field(default_factory=time.time)

# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v4.3 — Provider Pool & History Tracking.

Infraestructura reutilizable para el orquestador de pensamiento:
pool de providers LLM y registro de historial.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from cortex.llm.provider import LLMProvider

__all__ = [
    "ProviderPool",
    "ThinkingRecord",
]

logger = logging.getLogger("cortex.thinking.pool")


# ─── Provider Pool ───────────────────────────────────────────────────


class ProviderPool:
    """Pool de LLMProviders reutilizables.

    Evita crear/destruir httpx.AsyncClient en cada query.
    Un provider por clave (provider_name, model).
    """

    def __init__(self) -> None:
        self._pool: dict[tuple[str, str], LLMProvider] = {}

    def get(self, provider_name: str, model: str) -> LLMProvider:
        """Obtiene o crea un provider del pool."""
        key = (provider_name, model)
        if key not in self._pool:
            self._pool[key] = LLMProvider(provider=provider_name, model=model)
            logger.debug("Pool: creado %s:%s", provider_name, model)
        return self._pool[key]

    async def close_all(self) -> None:
        """Cierra todos los providers del pool."""
        for key, provider in self._pool.items():
            try:
                await provider.close()
            except (OSError, ValueError, KeyError) as e:
                logger.debug("Pool: error cerrando %s: %s", key, e)
        self._pool.clear()

    @property
    def size(self) -> int:
        return len(self._pool)


# ─── History Tracking ────────────────────────────────────────────────


@dataclass
class ThinkingRecord:
    """Registro de un pensamiento para análisis retrospectivo."""

    mode: str
    strategy: str
    models_queried: int
    models_succeeded: int
    total_latency_ms: float
    confidence: float
    agreement: float
    winner: str | None = None
    timestamp: float = field(default_factory=time.time)

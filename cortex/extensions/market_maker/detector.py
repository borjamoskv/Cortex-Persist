"""Phase 1: Multi-Source Trend Detection.

Detects initial sparks. A signal is only valid if it reaches multi-source convergence.
"""

from __future__ import annotations

import logging
import random
from decimal import Decimal
from typing import Any, Protocol

from cortex.extensions.market_maker.models import TrendSignal

log = logging.getLogger(__name__)


class HttpClient(Protocol):
    """Protocol for an injectable HTTP client."""

    async def get(self, url: str) -> dict[str, Any]: ...


class TrendDetector:
    """Phase 1 Engine: Cross-references multiple sources to find pre-viral trends."""

    SOURCES = ("google_trends", "reddit", "hackernews", "x")

    def __init__(
        self,
        http_client: HttpClient | None = None,
        random_seed: int | None = None,
    ) -> None:
        self._http = http_client
        self._rng = random.Random(random_seed)

    async def scan(self, keywords: list[str]) -> list[TrendSignal]:
        """
        Escanea múltiples fuentes buscando convergencia (≥2 fuentes).

        Args:
            keywords: Tópicos semilla a explorar.

        Returns:
            Lista de señales que sobrevivieron al filtro de convergencia.
        """
        raw_signals: list[TrendSignal] = []

        for kw in keywords:
            sources: list[str] = []

            # Simulated HTTP scanning for Phase 1 Engine
            if self._rng.random() > 0.4:
                sources.append("google_trends")
            if self._rng.random() > 0.5:
                sources.append("reddit")
            if self._rng.random() > 0.6:
                sources.append("hackernews")
            if self._rng.random() > 0.5:
                sources.append("x")

            if sources:
                velocity = Decimal(str(round(self._rng.uniform(0.1, 5.0), 2)))
                signal = TrendSignal(
                    topic=kw,
                    source_count=len(sources),
                    sources=sources,
                    velocity=velocity,
                )
                raw_signals.append(signal)

        converged = self._convergence_filter(raw_signals)

        if raw_signals:
            log.info(
                "Detectadas %d señales crudas, %d convergieron (≥2 fuentes)",
                len(raw_signals),
                len(converged),
            )

        return converged

    def _convergence_filter(self, signals: list[TrendSignal]) -> list[TrendSignal]:
        """Solo sobrevivirán las señales que tengan acuerdo en más de 1 fuente."""
        return [s for s in signals if s.source_count >= 2]

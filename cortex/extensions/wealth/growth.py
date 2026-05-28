"""Sovereign Growth Engine v1.0.0.

Motor soberano de crecimiento acelerado. Detecta oportunidades de monetización
y ejecuta distribución de forma unificada.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

DEFAULT_CHANNELS = ("github", "reddit", "twitter", "hackernews")


@dataclass
class GrowthSignal:
    platform: str
    target_url: str
    topic: str
    urgency_score: float
    relevance_score: float
    alpha_score: float
    suggested_action: str

    def __repr__(self) -> str:
        return f"GrowthSignal({self.platform}:{self.topic[:30]}… α={self.alpha_score:.2f})"


class GrowthEngine:
    """Orchestrador del pipeline GTM y de Alpha Hunting."""

    def __init__(self, channels: tuple[str, ...] = DEFAULT_CHANNELS) -> None:
        self.channels = channels

    async def pulse_scan(self, keyword: str) -> list[GrowthSignal]:
        """Fase 0: Escaneo asíncrono de señales en tiempo real (Market Pulse)."""
        scanners = {
            "github": self._scan_github,
            "reddit": self._scan_reddit,
            "hackernews": self._scan_hackernews,
        }
        tasks = [scanners[ch](keyword) for ch in self.channels if ch in scanners]

        results = await asyncio.gather(*tasks)
        raw = [signal for sublist in results for signal in sublist]

        # Deduplicate by target_url — highest alpha_score wins
        deduped = self._deduplicate(raw)

        sorted_signals = sorted(deduped, key=lambda x: x.alpha_score, reverse=True)
        log.info(
            "Pulse scan '%s': %d señales raw → %d deduplicadas",
            keyword,
            len(raw),
            len(sorted_signals),
        )
        return sorted_signals

    @staticmethod
    def _deduplicate(signals: list[GrowthSignal]) -> list[GrowthSignal]:
        """Colapsa señales con la misma URL — gana la de mayor alpha_score."""
        best: dict[str, GrowthSignal] = {}
        for s in signals:
            if s.target_url not in best or s.alpha_score > best[s.target_url].alpha_score:
                best[s.target_url] = s
        return list(best.values())

    async def _scan_github(self, keyword: str) -> list[GrowthSignal]:
        """Mock scan of GitHub issues looking for pain points."""
        await asyncio.sleep(0.5)  # Simulate API latency

        signals = [
            GrowthSignal(
                platform="github",
                target_url="https://github.com/cpacker/MemGPT/issues/3179",
                topic="State Drift & Archival Timeout",
                urgency_score=8.5,
                relevance_score=9.0,
                alpha_score=8.75,
                suggested_action="Comment with CORTEX v6.0 Trust Infra architecture",
            ),
            GrowthSignal(
                platform="github",
                target_url="https://github.com/mem0ai/mem0/issues/402",
                topic="Deduplication failures in long-term memory",
                urgency_score=7.0,
                relevance_score=8.5,
                alpha_score=7.75,
                suggested_action="Comparative comment highlighting O(1) deduplication",
            ),
        ]
        log.debug("GitHub scan: %d señales para '%s'", len(signals), keyword)
        return signals

    async def _scan_reddit(self, keyword: str) -> list[GrowthSignal]:
        """Mock scan of Reddit looking for trending conversations."""
        await asyncio.sleep(0.6)

        signals = [
            GrowthSignal(
                platform="reddit",
                target_url="r/LocalLLaMA",
                topic=f"Best agent framework for {keyword}?",
                urgency_score=6.5,
                relevance_score=8.0,
                alpha_score=7.25,
                suggested_action=("Create long-form AMA thread explaining CORTEX memory manifold"),
            ),
        ]
        log.debug("Reddit scan: %d señales para '%s'", len(signals), keyword)
        return signals

    async def _scan_hackernews(self, keyword: str) -> list[GrowthSignal]:
        """Mock scan of HackerNews."""
        await asyncio.sleep(0.3)
        return []

    async def orchestrate_distribution(self, signal: GrowthSignal) -> bool:
        """
        Fase 4: Ejecución orquestada.
        Toma una señal Alpha, genera contenido y distribuye.
        """
        log.info("Distribuyendo en %s: %s", signal.platform, signal.target_url)
        await asyncio.sleep(0.5)
        return True

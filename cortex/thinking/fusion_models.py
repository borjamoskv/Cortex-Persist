# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v4.3 — Fusion Data Models & Utilities.

Dataclasses, enums, y utilidades de tokenización compartidas
por el motor de fusión y otros módulos del paquete thinking.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ─── Constantes ──────────────────────────────────────────────────────

# Palabras demasiado comunes para afectar el agreement
_STOPWORDS = frozenset(
    {
        "the",
        "is",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "it",
        "that",
        "this",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "can",
        "not",
        "no",
        "so",
        "if",
        "then",
        "than",
        "more",
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "de",
        "del",
        "en",
        "con",
        "por",
        "para",
        "que",
        "es",
        "son",
        "como",
        "más",
        "pero",
        "sin",
    }
)

_PUNCT_RE = re.compile(r"[.,!?;:\"'()\[\]{}—–\-/\\<>@#$%^&*~`|+=]")


# ─── Enums ───────────────────────────────────────────────────────────


class FusionStrategy(str, Enum):
    """Estrategia de fusión de pensamiento."""

    MAJORITY = "majority"
    SYNTHESIS = "synthesis"
    BEST_OF_N = "best_of_n"
    WEIGHTED_SYNTHESIS = "weighted_synthesis"


# ─── Data Classes ────────────────────────────────────────────────────


@dataclass(slots=True)
class ModelResponse:
    """Respuesta de un modelo individual."""

    provider: str
    model: str
    content: str
    latency_ms: float = 0.0
    error: str | None = None
    token_count: int = 0  # Tokens usados (estimación)

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.content)

    @property
    def label(self) -> str:
        """ID legible: 'provider:model'."""
        return f"{self.provider}:{self.model}"


@dataclass(slots=True)
class FusedThought:
    """Resultado de la fusión multi-modelo."""

    content: str
    strategy: FusionStrategy
    confidence: float  # 0.0-1.0
    sources: list[ModelResponse] = field(default_factory=list)
    agreement_score: float = 0.0
    meta: dict = field(default_factory=dict)

    @property
    def source_count(self) -> int:
        return sum(1 for s in self.sources if s.ok)

    @property
    def fastest_source(self) -> ModelResponse | None:
        ok_sources = [s for s in self.sources if s.ok]
        return min(ok_sources, key=lambda s: s.latency_ms) if ok_sources else None

    @property
    def slowest_source(self) -> ModelResponse | None:
        ok_sources = [s for s in self.sources if s.ok]
        return max(ok_sources, key=lambda s: s.latency_ms) if ok_sources else None

    def summary(self) -> dict[str, Any]:
        """Resumen compacto para logging/métricas."""
        return {
            "strategy": self.strategy.value,
            "confidence": round(self.confidence, 3),
            "agreement": round(self.agreement_score, 3),
            "sources_ok": self.source_count,
            "sources_total": len(self.sources),
            "fastest_ms": round(self.fastest_source.latency_ms, 1) if self.fastest_source else None,
            "slowest_ms": round(self.slowest_source.latency_ms, 1) if self.slowest_source else None,
        }


@dataclass
class _ModelStats:
    """Estadísticas acumuladas por modelo."""

    wins: int = 0
    participations: int = 0
    total_latency_ms: float = 0.0

    @property
    def win_rate(self) -> float:
        return self.wins / self.participations if self.participations else 0.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.participations if self.participations else 0.0


class ThinkingHistory:
    """Historial acumulado de fusiones — win rates y latencias por modelo."""

    def __init__(self):
        self._stats: dict[str, _ModelStats] = defaultdict(_ModelStats)
        self._total_fusions: int = 0

    def record(self, result: FusedThought) -> None:
        self._total_fusions += 1
        winner_label = result.meta.get("winner")
        for src in result.sources:
            if not src.ok:
                continue
            s = self._stats[src.label]
            s.participations += 1
            s.total_latency_ms += src.latency_ms
            if src.label == winner_label:
                s.wins += 1

    def top_models(self, n: int = 5) -> list[dict[str, Any]]:
        ranked = sorted(
            self._stats.items(),
            key=lambda kv: kv[1].win_rate,
            reverse=True,
        )
        return [
            {
                "model": label,
                "win_rate": round(s.win_rate, 3),
                "avg_latency_ms": round(s.avg_latency_ms, 1),
                "participations": s.participations,
                "wins": s.wins,
            }
            for label, s in ranked[:n]
        ]

    @property
    def total_fusions(self) -> int:
        return self._total_fusions


# ─── Tokenización ───────────────────────────────────────────────────


def _tokenize(text: str) -> set[str]:
    """Tokeniza texto en un set de palabras normalizadas.

    Elimina puntuación, stopwords, y tokens muy cortos.
    Reutilizado por _calculate_agreement y _fuse_majority para
    evitar duplicación.
    """
    cleaned = _PUNCT_RE.sub(" ", text.lower())
    return {w for w in cleaned.split() if len(w) > 2 and w not in _STOPWORDS}


def _jaccard(set_a: set[str], set_b: set[str]) -> float:
    """Similitud Jaccard entre dos conjuntos."""
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)

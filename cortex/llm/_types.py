# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX LLM — Domain types and data-transfer objects.

Axiom: Ω₂ (Landauer's Razor) — each type lives in exactly one place.
These are pure data classes with no runtime dependencies on providers
or routing logic. Import cost: zero.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

# ─── Intent Classification ─────────────────────────────────────────────────


class IntentProfile(str, Enum):
    """Clasificación soberana de la intención del prompt.

    Permite al router seleccionar fallbacks con afinidad semántica,
    evitando que el ruido del error se propague entre dominios.
    """

    CODE = "code"
    """Generación, refactoring, debugging o análisis de código."""

    REASONING = "reasoning"
    """Análisis multi-paso, matemáticas, planificación estructurada."""

    CREATIVE = "creative"
    """Escritura, brainstorming, contenido narrativo."""

    GENERAL = "general"
    """Intención genérica o no clasificada — sin restricción de fallback."""


class CascadeTier(str, Enum):
    """Classification of which cascade tier resolved the call."""

    PRIMARY = "primary"
    TYPED_MATCH = "typed-match"
    SAFETY_NET = "safety-net"
    NONE = "none"  # all providers failed


@dataclass(frozen=True, slots=True)
class CascadeEvent:
    """Structured trace for a single execute_resilient call.

    Enables production measurement of entropy delta:
    - typed-match = entropy-neutral (domain preserved)
    - safety-net  = entropy-elevated (domain crossed)
    """

    intent: IntentProfile
    resolved_by: str | None
    resolved_tier: CascadeTier
    cascade_depth: int  # how many providers attempted before success
    primary_consecutive_failures: int  # session counter at call time
    timestamp: float = field(default_factory=time.monotonic)


@dataclass(frozen=True, slots=True)
class HedgedResult:
    """Observability payload for hedged request races.

    Captures which provider won, response latency, and which providers
    were cancelled. Essential for tuning hedging_peers configuration.
    """

    winner: str
    """provider_name of the winning provider."""

    response: str
    """Response content from the winner."""

    latency_ms: float
    """Wall-clock latency of the winning provider (ms)."""

    cancelled: tuple[str, ...] = ()
    """provider_names of cancelled (loser) providers."""


__all__ = [
    "CascadeEvent",
    "CascadeTier",
    "HedgedResult",
    "IntentProfile",
]

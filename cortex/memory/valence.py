"""CORTEX v6+ — Emotional Valence Tagging (Amygdala Artificial).

Strategy #3: Memories with emotional charge are stored more
strongly. The amygdala doesn't just tag — it AMPLIFIES consolidation
via noradrenaline-mediated LTP enhancement.

Valence spectrum:
  +1.0 = Critical lesson (error that cost hours)
   0.0 = Neutral decision
  -1.0 = Anti-pattern (confirmed failure to avoid)

Both extremes (+1 and -1) get HIGHER energy than neutral.
Anti-patterns are as valuable as patterns.
"""

from __future__ import annotations

import enum
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger("cortex.memory.valence")


class EmotionalTag(str, enum.Enum):
    """Discrete emotional categories for memory tagging."""

    CRITICAL = "critical"  # Must never forget (errors, breakthroughs)
    POSITIVE = "positive"  # Success, good pattern
    NEUTRAL = "neutral"  # Standard fact
    NEGATIVE = "negative"  # Failed attempt
    ANTI_PATTERN = "anti_pattern"  # Confirmed bad practice


class ValenceRecord(BaseModel):
    """Emotional valence metadata for an engram."""

    valence: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Emotional valence: -1 (anti-pattern) to +1 (critical).",
    )
    tag: EmotionalTag = Field(
        default=EmotionalTag.NEUTRAL,
        description="Discrete emotional category.",
    )
    arousal: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Arousal level — how activating this memory is.",
    )

    @property
    def energy_multiplier(self) -> float:
        """Compute energy multiplier from valence and arousal.

        Both extreme positive AND negative valences get boosted.
        Neutral memories decay normally. High arousal amplifies.

        Returns a multiplier in range [0.5, 2.0].
        """
        # Absolute valence: both extremes are important
        intensity = abs(self.valence)
        # Base multiplier: 1.0 at neutral, up to 2.0 at extremes
        base = 1.0 + intensity
        # Arousal scales the effect
        return min(2.0, base * (0.5 + 0.5 * self.arousal))


def classify_valence(content: str, fact_type: str = "") -> ValenceRecord:
    """Auto-classify emotional valence from content heuristics.

    This is a fast heuristic classifier. For production,
    replace with LLM-based classification.
    """
    content_lower = content.lower()

    # Error indicators → high negative valence, high arousal
    error_signals = ("error", "bug", "crash", "failed", "broke", "fix")
    if fact_type == "error" or any(s in content_lower for s in error_signals):
        return ValenceRecord(
            valence=-0.8,
            tag=EmotionalTag.NEGATIVE,
            arousal=0.9,
        )

    # Decision indicators → moderate positive valence
    if fact_type == "decision":
        return ValenceRecord(
            valence=0.6,
            tag=EmotionalTag.POSITIVE,
            arousal=0.7,
        )

    # Bridge indicators → high positive (cross-project learning)
    if fact_type == "bridge":
        return ValenceRecord(
            valence=0.9,
            tag=EmotionalTag.CRITICAL,
            arousal=0.8,
        )

    # Rule/axiom → critical, must persist
    if fact_type == "rule":
        return ValenceRecord(
            valence=1.0,
            tag=EmotionalTag.CRITICAL,
            arousal=0.6,
        )

    return ValenceRecord()

"""CORTEX v7+ — Procedural Memory & Skill Buffer.

Basal Ganglia analogue: caches recently executed skills, tracking
execution outcomes (striatal valuation) and latencies. Shifts
skill selection from pure semantic matching to reinforcement-based
historical reliability.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import ClassVar, Final

# ─── Constants ──────────────────────────────────────────────────────────────

# EMA alpha for success rate updates — higher = reacts faster to recent outcomes
_ALPHA_SUCCESS: Final[float] = 0.3

# EMA alpha for latency updates — lower = more stable average
_ALPHA_LATENCY: Final[float] = 0.2

# Temporal decay half-life: striatal value halves every N seconds of disuse
# Set to 30 days (2.592e6 seconds) — matches biological dopaminergic pruning timescale
_DECAY_HALFLIFE_SECONDS: Final[float] = 30 * 24 * 3600.0


# ─── Models ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ProceduralEngram:
    """Frozen representation of a skill's reinforcement history."""

    skill_name: str
    invocations: int = 0
    success_rate: float = 1.0
    avg_latency_ms: float = 0.0
    last_invoked: float = field(default_factory=time.time)
    permanent: bool = False
    """If True, skip temporal decay — skill is always fully valued."""

    @property
    def striatal_value(self) -> float:
        """Valuation score — combines success rate, usage frequency, and recency decay.

        Analogue to Striatal valuation in the Basal Ganglia:
          - Success rate is the primary driver.
          - Frequency (log-scaled) provides a small bonus for well-practiced skills.
          - Temporal decay penalizes skills not used recently (dopaminergic pruning).
            A skill unused for 30 days recovers 50% of its potential score at most.
        """
        frequency_bonus = math.log10(self.invocations + 1) * 0.1
        raw = min(1.0, self.success_rate + frequency_bonus)

        if self.permanent:
            return raw

        # Exponential decay: value *= 2^(-elapsed / halflife)
        elapsed = max(0.0, time.time() - self.last_invoked)
        decay = math.pow(2.0, -elapsed / _DECAY_HALFLIFE_SECONDS)
        return raw * decay


# ─── Memory ─────────────────────────────────────────────────────────────────


class ProceduralMemory:
    """Skill Buffer with reinforcement tracking.

    Provides O(1) access to execution history for any skill slug,
    updating EMA success rates and latencies on each invocation.
    """

    BASELINE_LATENCY_MS: ClassVar[float] = 100.0

    def __init__(self) -> None:
        self._buffer: dict[str, ProceduralEngram] = {}

    def get_engram(self, skill_name: str) -> ProceduralEngram | None:
        """Fetch the engram for a specific skill. O(1)."""
        return self._buffer.get(skill_name)

    def record_execution(
        self,
        skill_name: str,
        success: bool,
        latency_ms: float,
        permanent: bool = False,
    ) -> None:
        """Record the outcome of a skill execution.

        Updates EMA success rate and latency.
        Time complexity: O(1).
        """
        existing = self._buffer.get(skill_name)
        now = time.time()

        if not existing:
            self._buffer[skill_name] = ProceduralEngram(
                skill_name=skill_name,
                invocations=1,
                success_rate=1.0 if success else 0.0,
                avg_latency_ms=latency_ms,
                last_invoked=now,
                permanent=permanent,
            )
            return

        outcome = 1.0 if success else 0.0
        new_success_rate = _ALPHA_SUCCESS * outcome + (1.0 - _ALPHA_SUCCESS) * existing.success_rate
        new_avg_latency = (
            _ALPHA_LATENCY * latency_ms + (1.0 - _ALPHA_LATENCY) * existing.avg_latency_ms
        )

        self._buffer[skill_name] = ProceduralEngram(
            skill_name=skill_name,
            invocations=existing.invocations + 1,
            success_rate=new_success_rate,
            avg_latency_ms=new_avg_latency,
            last_invoked=now,
            permanent=permanent or existing.permanent,
        )

    def top_skills(self, limit: int = 5) -> list[ProceduralEngram]:
        """Return the highest-value skills by striatal valuation."""
        engrams = sorted(self._buffer.values(), key=lambda x: x.striatal_value, reverse=True)
        return engrams[:limit]

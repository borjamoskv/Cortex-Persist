# cortex/evolution/landscape.py
"""Dynamic Fitness Landscape — the ceiling that moves.

The fitness ceiling is not a constant. It grows with the ecosystem:
- More active projects → higher ceiling
- More bridge facts → higher ceiling
- More skills → higher ceiling
- More unresolved ghosts → challenges that raise the bar

This prevents premature convergence: agents can never "finish"
because the landscape evolves with MOSKV-1.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.evolution.agents import SovereignAgent

logger = logging.getLogger(__name__)

# MOSKV-1 known project roots
_PROJECT_ROOTS = [
    Path("~/cortex").expanduser(),
    Path("~/notch-live").expanduser(),
    Path("~/naroa-2026").expanduser(),
    Path("~/mixcraft").expanduser(),
]

_SKILLS_DIR = Path("~/.gemini/antigravity/skills").expanduser()

# Weights
_BASE_CEILING = 100.0
_PER_PROJECT = 15.0
_PER_BRIDGE = 5.0
_PER_SKILL = 2.0
_PER_GHOST = 3.0
_PER_DECISION = 1.0

# Cache TTL (seconds)
_CACHE_TTL = 30.0


@dataclass
class LandscapeState:
    """Snapshot of the ecosystem complexity at a point in time."""

    active_projects: int = 0
    bridge_count: int = 0
    ghost_count: int = 0
    skill_count: int = 0
    decision_count: int = 0
    error_count: int = 0
    ceiling: float = _BASE_CEILING
    computed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_projects": self.active_projects,
            "bridge_count": self.bridge_count,
            "ghost_count": self.ghost_count,
            "skill_count": self.skill_count,
            "decision_count": self.decision_count,
            "error_count": self.error_count,
            "ceiling": round(self.ceiling, 1),
        }


class FitnessLandscape:
    """Computes a dynamic fitness ceiling from live ecosystem state.

    Fully synchronous — no async DB calls. Uses filesystem
    (project dirs, skill dirs, context-snapshot.md) for speed.
    """

    def __init__(self) -> None:
        self._cache: LandscapeState | None = None
        self._last_ceiling: float = _BASE_CEILING

    def compute(self) -> LandscapeState:
        """Full landscape snapshot; cached for TTL seconds."""
        now = time.time()
        if self._cache and (now - self._cache.computed_at) < _CACHE_TTL:
            return self._cache

        projects = self._count_projects()
        skills = self._count_skills()
        facts = self._count_facts()

        ceiling = (
            _BASE_CEILING
            + projects * _PER_PROJECT
            + facts.get("bridge", 0) * _PER_BRIDGE
            + skills * _PER_SKILL
            + facts.get("ghost", 0) * _PER_GHOST
            + facts.get("decision", 0) * _PER_DECISION
        )

        # Ratchet — ceiling never decreases
        ceiling = max(ceiling, self._last_ceiling)
        self._last_ceiling = ceiling

        state = LandscapeState(
            active_projects=projects,
            bridge_count=facts.get("bridge", 0),
            ghost_count=facts.get("ghost", 0),
            skill_count=skills,
            decision_count=facts.get("decision", 0),
            error_count=facts.get("error", 0),
            ceiling=ceiling,
            computed_at=now,
        )
        self._cache = state

        logger.debug(
            "Landscape: projects=%d skills=%d bridges=%d ghosts=%d → ceiling=%.0f",
            projects,
            skills,
            facts.get("bridge", 0),
            facts.get("ghost", 0),
            ceiling,
        )
        return state

    @property
    def ceiling(self) -> float:
        """Current ceiling (sync access to cached value)."""
        if not self._cache:
            self.compute()
        return self._last_ceiling

    def clamp(self, agent: SovereignAgent) -> None:
        """Clamp agent + subagent fitness to the current ceiling.

        Call after all mutations in a cycle. Uses cached ceiling
        (compute() must have been called earlier in the cycle).
        """
        ceil = self._last_ceiling
        agent.fitness = min(ceil, max(0.0, agent.fitness))
        for sub in agent.subagents:
            sub.fitness = min(ceil, max(0.0, sub.fitness))

    # ── Internal ───────────────────────────────────────────────

    @staticmethod
    def _count_projects() -> int:
        return sum(1 for p in _PROJECT_ROOTS if p.exists() and p.is_dir())

    @staticmethod
    def _count_skills() -> int:
        if not _SKILLS_DIR.exists():
            return 0
        return sum(
            1 for d in _SKILLS_DIR.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))
        )

    @staticmethod
    def _count_facts() -> dict[str, int]:
        """Parse context-snapshot.md for rough fact counts."""
        counts = {"bridge": 0, "ghost": 0, "decision": 0, "error": 0}
        snapshot = Path("~/.cortex/context-snapshot.md").expanduser()
        if not snapshot.exists():
            return counts
        try:
            text = snapshot.read_text(encoding="utf-8", errors="ignore").lower()
            for line in text.splitlines():
                for key in counts:
                    if key in line:
                        counts[key] += 1
        except OSError:
            pass
        return counts

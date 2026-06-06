# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(kw_only=True)
class GeneFragment:
    """A shareable piece of a strategy genome.

    Can be a single heuristic, a tool ordering, or an
    exploration rate setting that proved successful.
    """

    fragment_id: str
    donor_agent: str
    donor_generation: int
    fragment_type: str  # "heuristic" | "tool_order" | "exploration_rate" | "genome"
    payload: dict[str, Any]  # Actual genetic material
    fitness_at_donation: float
    donation_time: float = field(default_factory=time.monotonic)
    adoption_count: int = 0
    adoption_success_count: int = 0

    @property
    def adoption_success_rate(self) -> float:
        if self.adoption_count == 0:
            return 0.5  # Prior
        return self.adoption_success_count / self.adoption_count

    @property
    def value_score(self) -> float:
        """Combined score: donor fitness + adoption success."""
        return self.fitness_at_donation * 0.4 + self.adoption_success_rate * 0.6


@dataclass(kw_only=True)
class TournamentResult:
    """Result of a genome tournament."""

    winner: str  # agent_id
    rankings: list[tuple[str, float]]  # [(agent_id, score)]
    selection_pressure: float  # How much the winner dominated


@dataclass(kw_only=True)
class AgentSpecialization:
    """Detected specialization of an agent."""

    agent_id: str
    primary_role: str  # "searcher" | "deployer" | "verifier" | "generalist"
    role_confidence: float
    dominant_tools: list[str]
    dominant_heuristics: list[str]
    fitness_in_role: float

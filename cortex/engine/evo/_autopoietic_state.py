# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AutopoieticState:
    """Observable state of the autopoietic agent for monitoring."""

    current_generation: int = 0
    current_genome_hash: str = ""
    best_fitness_ever: float = 0.0
    current_fitness: float = 0.0
    fitness_trend: float = 0.0
    generations_without_improvement: int = 0
    total_mutations: int = 0
    total_adoptions: int = 0
    total_discards: int = 0
    total_rollbacks: int = 0
    total_agents_spawned: int = 0
    meta_mutations: int = 0
    is_evolving: bool = False
    last_evolution_ms: float = 0.0
    checkpoint_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_generation": self.current_generation,
            "current_genome_hash": self.current_genome_hash,
            "best_fitness_ever": round(self.best_fitness_ever, 4),
            "current_fitness": round(self.current_fitness, 4),
            "fitness_trend": round(self.fitness_trend, 4),
            "generations_without_improvement": self.generations_without_improvement,
            "total_mutations": self.total_mutations,
            "total_adoptions": self.total_adoptions,
            "total_discards": self.total_discards,
            "total_rollbacks": self.total_rollbacks,
            "total_agents_spawned": self.total_agents_spawned,
            "meta_mutations": self.meta_mutations,
            "is_evolving": self.is_evolving,
            "last_evolution_ms": round(self.last_evolution_ms, 2),
            "checkpoint_count": self.checkpoint_count,
        }

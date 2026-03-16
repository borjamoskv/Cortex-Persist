from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class DomainMetrics:
    """CortexMetrics data structure representing domain health telemetry.
    Maps to the synchronized SQLite3 backend with 60s TTL cache.
    """

    domain_id: str
    health_score: float = 1.0
    error_rate: float = 0.0
    ghost_density: float = 0.0
    fact_density: float = 0.0
    bridge_score: float = 0.0
    fitness_delta: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def is_stale(self, ttl_seconds: int = 60) -> bool:
        return (time.time() - self.timestamp) > ttl_seconds


@dataclass
class Mutation:
    """Genotype representation passed to execution environment."""

    mutation_id: str
    parameters: dict[str, float] = field(default_factory=dict)
    generation: int = 0
    fitness: float = 0.0
    history_log: list[str] = field(default_factory=list)
    entropy_resistance: float = 1.0

    def record_change(self, change_desc: str) -> None:
        self.history_log.append(f"{time.time()}: {change_desc}")


@dataclass
class SubAgent:
    """Individual agent within a sovereign domain."""

    agent_id: str
    mutation: Mutation
    domain_id: str
    fitness: float = 0.0
    generation: int = 0
    is_active: bool = True

    def __post_init__(self) -> None:
        if self.mutation.mutation_id != self.agent_id:
            msg = f"Inconsistent mutation_id for agent {self.agent_id}"
            raise ValueError(msg)


@dataclass
class SovereignAgent:
    """Top-level autonomous agent containing sub-agent population."""

    sovereign_id: str
    domain_id: str
    subagents: list[SubAgent] = field(default_factory=list)
    creation_timestamp: float = field(default_factory=time.time)

    def get_best_subagent(self) -> SubAgent | None:
        if not self.subagents:
            return None
        return max(self.subagents, key=lambda s: s.fitness)

    def get_worst_subagent(self) -> SubAgent | None:
        if not self.subagents:
            return None
        return min(self.subagents, key=lambda s: s.fitness)

    def get_fitness_variance(self) -> float:
        if len(self.subagents) < 2:
            return 0.0
        mn = sum(s.fitness for s in self.subagents) / len(self.subagents)
        variance = sum((s.fitness - mn) ** 2 for s in self.subagents) / len(self.subagents)
        return variance


class ImprovementStrategy(Protocol):
    """Protocol for pluggable evolutionary improvement strategies."""

    def evaluate(
        self,
        sovereign: SovereignAgent,
        subagent: SubAgent,
        metrics: DomainMetrics,
        cortex_metrics: Any,
    ) -> dict[str, Any] | None: ...

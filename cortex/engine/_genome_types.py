# [C5-REAL] Exergy-Maximized
"""FitnessRecord, Lineage, MutationType, and StrategyGenome definition.

Reality Level: C5-REAL
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cortex.isa.builder import (
    AgentOp,
    dispatch_targets,
    node_count,
    noop,
)

logger = logging.getLogger("cortex.engine.genome")


@dataclass
class FitnessRecord:
    """Single fitness measurement from an evaluation run."""

    score: float
    latency_ms: float
    success: bool
    error_rate: float
    throughput: float  # ops/sec
    timestamp: float = field(default_factory=time.monotonic)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "error_rate": self.error_rate,
            "throughput": self.throughput,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class Lineage:
    """Evolutionary history of a genome across generations."""

    generation: int = 0
    parent_hash: str = "GENESIS"
    fitness_history: list[FitnessRecord] = field(default_factory=list)
    mutation_log: list[str] = field(default_factory=list)
    adopted_count: int = 0
    discarded_count: int = 0
    children_spawned: int = 0

    @property
    def avg_fitness(self) -> float:
        if not self.fitness_history:
            return 0.0
        return sum(r.score for r in self.fitness_history) / len(self.fitness_history)

    @property
    def best_fitness(self) -> float:
        if not self.fitness_history:
            return 0.0
        return max(r.score for r in self.fitness_history)

    @property
    def fitness_trend(self) -> float:
        """Slope of fitness over recent history. Positive = improving."""
        if len(self.fitness_history) < 3:
            return 0.0
        recent = self.fitness_history[-5:]
        n = len(recent)
        x_mean = (n - 1) / 2.0
        y_mean = sum(r.score for r in recent) / n
        numerator = sum((i - x_mean) * (r.score - y_mean) for i, r in enumerate(recent))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        return numerator / denominator if denominator > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "parent_hash": self.parent_hash,
            "avg_fitness": self.avg_fitness,
            "best_fitness": self.best_fitness,
            "fitness_trend": self.fitness_trend,
            "adopted_count": self.adopted_count,
            "discarded_count": self.discarded_count,
            "children_spawned": self.children_spawned,
            "mutation_log_tail": self.mutation_log[-5:] if self.mutation_log else [],
        }


class MutationType(str, Enum):
    """Categories of genome mutation - from conservative to radical."""

    PARAMETER_DRIFT = "parameter_drift"
    SUBTREE_SWAP = "subtree_swap"
    NODE_INSERT = "node_insert"
    NODE_DELETE = "node_delete"
    PARALLELIZE = "parallelize"
    SEQUENTIALIZE = "sequentialize"
    LOOP_UNROLL = "loop_unroll"
    CONDITIONAL_INJECT = "conditional_inject"
    STRATEGY_SYNTHESIS = "strategy_synthesis"
    META_MUTATION = "meta_mutation"
    CAUSAL_PATCH = "causal_patch"


class StrategyGenome:
    """A self-describing, self-modifiable agent strategy."""

    def __init__(
        self,
        *,
        name: str = "unnamed",
        dispatch_tree: AgentOp | None = None,
        parameters: dict[str, Any] | None = None,
        mutation_rates: dict[str, float] | None = None,
        constraints: list[str] | None = None,
    ) -> None:
        self.name = name
        self.dispatch_tree: AgentOp = dispatch_tree or noop()
        self.parameters: dict[str, Any] = parameters or {}
        self.mutation_rates: dict[str, float] = mutation_rates or {
            MutationType.CAUSAL_PATCH: 0.20,
            MutationType.PARAMETER_DRIFT: 0.30,
            MutationType.SUBTREE_SWAP: 0.10,
            MutationType.NODE_INSERT: 0.10,
            MutationType.NODE_DELETE: 0.03,
            MutationType.PARALLELIZE: 0.05,
            MutationType.SEQUENTIALIZE: 0.05,
            MutationType.LOOP_UNROLL: 0.03,
            MutationType.CONDITIONAL_INJECT: 0.05,
            MutationType.STRATEGY_SYNTHESIS: 0.04,
            MutationType.META_MUTATION: 0.05,
        }
        self.constraints: list[str] = constraints or []
        self.lineage = Lineage()
        self._hash: str | None = None

    @property
    def genome_hash(self) -> str:
        """Content-addressable hash of the genome (deterministic identity)."""
        if self._hash is None:
            hashable = {
                "name": self.name,
                "dispatch_tree": self.dispatch_tree,
                "parameters": self.parameters,
                "mutation_rates": self.mutation_rates,
                "constraints": self.constraints,
            }
            content = json.dumps(hashable, sort_keys=True, default=str)
            self._hash = hashlib.sha3_256(content.encode()).hexdigest()[:16]
        return self._hash

    def _invalidate_hash(self) -> None:
        self._hash = None

    def to_dict(self) -> dict[str, Any]:
        """Freeze the entire genome to a dict (quote)."""
        return {
            "name": self.name,
            "dispatch_tree": self.dispatch_tree,
            "parameters": self.parameters,
            "mutation_rates": self.mutation_rates,
            "constraints": self.constraints,
            "lineage": self.lineage.to_dict(),
            "genome_hash": self.genome_hash,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StrategyGenome:
        """Reconstruct genome from dict (unquote)."""
        genome = cls(
            name=data.get("name", "unnamed"),
            dispatch_tree=data.get("dispatch_tree"),
            parameters=data.get("parameters", {}),
            mutation_rates=data.get("mutation_rates", {}),
            constraints=data.get("constraints", []),
        )
        lineage_data = data.get("lineage", {})
        genome.lineage.generation = lineage_data.get("generation", 0)
        genome.lineage.parent_hash = lineage_data.get("parent_hash", "GENESIS")
        return genome

    @classmethod
    def from_json(cls, json_str: str) -> StrategyGenome:
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def clone(self) -> StrategyGenome:
        """Deep clone the genome (for mutation without affecting original)."""
        cloned = StrategyGenome(
            name=f"{self.name}_clone",
            dispatch_tree=copy.deepcopy(self.dispatch_tree),
            parameters=copy.deepcopy(self.parameters),
            mutation_rates=copy.deepcopy(self.mutation_rates),
            constraints=list(self.constraints),
        )
        cloned.lineage.generation = self.lineage.generation
        cloned.lineage.parent_hash = self.genome_hash
        return cloned

    def record_fitness(self, record: FitnessRecord) -> None:
        """Record a fitness measurement."""
        self.lineage.fitness_history.append(record)
        if len(self.lineage.fitness_history) > 100:
            self.lineage.fitness_history = self.lineage.fitness_history[-50:]

    @property
    def complexity(self) -> int:
        """Number of nodes in the dispatch tree."""
        return node_count(self.dispatch_tree)

    @property
    def targets(self) -> list[str]:
        """All dispatch targets in the tree."""
        return dispatch_targets(self.dispatch_tree)

    @property
    def parameter_count(self) -> int:
        return len(self.parameters)

    def introspect(self) -> dict[str, Any]:
        """Full self-inspection report."""
        return {
            "name": self.name,
            "genome_hash": self.genome_hash,
            "generation": self.lineage.generation,
            "complexity": self.complexity,
            "targets": self.targets,
            "parameter_count": self.parameter_count,
            "avg_fitness": self.lineage.avg_fitness,
            "best_fitness": self.lineage.best_fitness,
            "fitness_trend": self.lineage.fitness_trend,
            "mutation_rates": self.mutation_rates,
            "constraints": self.constraints,
        }

    def __repr__(self) -> str:
        return (
            f"<StrategyGenome name={self.name!r} gen={self.lineage.generation} "
            f"hash={self.genome_hash[:8]} fitness={self.lineage.avg_fitness:.2f} "
            f"complexity={self.complexity}>"
        )

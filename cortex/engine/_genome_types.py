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
from cortex.math.babylon import Babylon60

logger = logging.getLogger("cortex.engine.genome")


@dataclass
class FitnessRecord:
    """Single fitness measurement from an evaluation run."""

    score: Babylon60
    latency_ms: Babylon60
    success: bool
    error_rate: Babylon60
    throughput: Babylon60  # ops/sec
    timestamp: Babylon60 = field(default_factory=lambda: Babylon60.from_int(time.monotonic_ns() // 1_000_000))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        # BOUNDARY: Serialización a floats para trazabilidad visual (MongoDB/JSON)
        return {
            "score": self.score.to_float(),
            "latency_ms": self.latency_ms.to_float(),
            "success": self.success,
            "error_rate": self.error_rate.to_float(),
            "throughput": self.throughput.to_float(),
            "timestamp": self.timestamp.to_float(),
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
    def avg_fitness(self) -> Babylon60:
        if not self.fitness_history:
            return Babylon60.from_int(0)
        return sum((r.score for r in self.fitness_history), start=Babylon60.from_int(0)) / Babylon60.from_int(len(self.fitness_history))

    @property
    def best_fitness(self) -> Babylon60:
        if not self.fitness_history:
            return Babylon60.from_int(0)
        return max(r.score for r in self.fitness_history)

    @property
    def fitness_trend(self) -> Babylon60:
        """Slope of fitness over recent history. Positive = improving."""
        if len(self.fitness_history) < 3:
            return Babylon60.from_int(0)
        recent = self.fitness_history[-5:]
        n = len(recent)
        x_mean = Babylon60.from_int(n - 1) / Babylon60.from_int(2)
        y_mean = sum((r.score for r in recent), start=Babylon60.from_int(0)) / Babylon60.from_int(n)
        
        numerator = sum(
            ((Babylon60.from_int(i) - x_mean) * (r.score - y_mean) for i, r in enumerate(recent)), 
            start=Babylon60.from_int(0)
        )
        denominator = sum(
            ((Babylon60.from_int(i) - x_mean) * (Babylon60.from_int(i) - x_mean) for i in range(n)), 
            start=Babylon60.from_int(0)
        )
        return numerator / denominator if denominator.value > 0 else Babylon60.from_int(0)

    def to_dict(self) -> dict[str, Any]:
        # BOUNDARY: Serialización a floats para representación visual
        return {
            "generation": self.generation,
            "parent_hash": self.parent_hash,
            "avg_fitness": self.avg_fitness.to_float(),
            "best_fitness": self.best_fitness.to_float(),
            "fitness_trend": self.fitness_trend.to_float(),
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
        mutation_rates: dict[str, Babylon60] | None = None,
        constraints: list[str] | None = None,
    ) -> None:
        self.name = name
        self.dispatch_tree: AgentOp = dispatch_tree or noop()
        self.parameters: dict[str, Any] = parameters or {}
        self.mutation_rates: dict[str, Babylon60] = mutation_rates or {
            MutationType.CAUSAL_PATCH: Babylon60(43200),
            MutationType.PARAMETER_DRIFT: Babylon60(64800),
            MutationType.SUBTREE_SWAP: Babylon60(21600),
            MutationType.NODE_INSERT: Babylon60(21600),
            MutationType.NODE_DELETE: Babylon60(6480),
            MutationType.PARALLELIZE: Babylon60(10800),
            MutationType.SEQUENTIALIZE: Babylon60(10800),
            MutationType.LOOP_UNROLL: Babylon60(6480),
            MutationType.CONDITIONAL_INJECT: Babylon60(10800),
            MutationType.STRATEGY_SYNTHESIS: Babylon60(8640),
            MutationType.META_MUTATION: Babylon60(10800),
        }
        self.constraints: list[str] = constraints or []
        self.lineage = Lineage()
        self._hash: str | None = None

    @property
    def genome_hash(self) -> str:
        """Content-addressable hash of the genome (deterministic identity)."""
        if self._hash is None:
            serialized_rates = {str(k): v.value if hasattr(v, 'value') else v for k, v in self.mutation_rates.items()}
            serialized_params = {k: v.value if hasattr(v, 'value') else v for k, v in self.parameters.items()}
            hashable = {
                "name": self.name,
                "dispatch_tree": self.dispatch_tree,
                "parameters": serialized_params,
                "mutation_rates": serialized_rates,
                "constraints": self.constraints,
            }
            content = json.dumps(hashable, sort_keys=True, default=str)
            self._hash = hashlib.sha3_256(content.encode()).hexdigest()[:16]
        return self._hash

    def _invalidate_hash(self) -> None:
        self._hash = None

    def to_dict(self) -> dict[str, Any]:
        """Freeze the entire genome to a dict (quote)."""
        
        # Serialize Babylon60 inside mutation_rates
        serialized_rates = {}
        for k, v in self.mutation_rates.items():
            serialized_rates[str(k)] = v.value if hasattr(v, 'value') else v
            
        # Optional: serialize B60 in parameters
        serialized_params = {}
        for k, v in self.parameters.items():
            if hasattr(v, 'value'):
                serialized_params[k] = v.value
            else:
                serialized_params[k] = v

        return {
            "name": self.name,
            "dispatch_tree": self.dispatch_tree,
            "parameters": serialized_params,
            "mutation_rates": serialized_rates,
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
        
        # Deserialize mutation_rates to Babylon60
        raw_rates = data.get("mutation_rates", {})
        parsed_rates = {}
        for k, v in raw_rates.items():
            try:
                mt = MutationType(k)
                if isinstance(v, (int, float)):
                    # handle old floats, or direct values
                    if v < 1.0:
                        parsed_rates[mt] = Babylon60.from_float(float(v))
                    else:
                        parsed_rates[mt] = Babylon60(int(v))
                else:
                    parsed_rates[mt] = Babylon60(int(v))
            except Exception:
                pass
                
        # Parse parameters (if they were B60) - for simplicity we leave them as numbers unless specific
        # We don't have typed parameters, so we just pass them as they are
                
        genome = cls(
            name=data.get("name", "unnamed"),
            dispatch_tree=data.get("dispatch_tree"),
            parameters=data.get("parameters", {}),
            mutation_rates=parsed_rates,
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
            f"hash={self.genome_hash[:8]} fitness={float(self.lineage.avg_fitness):.2f} "  # type: ignore
            f"complexity={self.complexity}>"
        )

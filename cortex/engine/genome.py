"""Strategy Genome — Code-as-Data Foundation for L7 Autopoiesis.

A StrategyGenome is a serializable dict that encodes:
1. An ISA dispatch tree (the "phenotype" — what the agent DOES)
2. Strategy parameters (the "genotype" — HOW it does it)
3. Mutation operators (the "mutagen" — HOW it changes itself)
4. Fitness history (the "lineage" — HOW WELL it performed)

This is Python's answer to Lisp's code-as-data:
- quote  → to_dict() / to_json()  (freeze code into data)
- transform → mutate() / crossover()  (manipulate frozen code)
- eval  → compile() / execute()  (thaw data back into code)

The genome is the unit of evolution. Everything the agent IS
can be serialized, mutated, measured, and selected.

Reality Level: C5-REAL
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from cortex.isa.builder import (
    AgentOp,
    dispatch,
    seq,
    par,
    cond,
    loop_n,
    bind,
    halt,
    noop,
    reflect,
    rewrite,
    node_count,
    dispatch_targets,
    Predicate,
    SelfQuery,
)

__all__ = [
    "StrategyGenome",
    "GenomeMutator",
    "MutationType",
    "FitnessRecord",
    "Lineage",
]

logger = logging.getLogger("cortex.engine.genome")


# ─── Fitness Record ──────────────────────────────────────────────


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


# ─── Mutation Types ──────────────────────────────────────────────


class MutationType(str, Enum):
    """Categories of genome mutation — from conservative to radical."""

    # Conservative: tweak parameters within existing structure
    PARAMETER_DRIFT = "parameter_drift"
    # Moderate: swap subtrees or insert/remove nodes
    SUBTREE_SWAP = "subtree_swap"
    NODE_INSERT = "node_insert"
    NODE_DELETE = "node_delete"
    # Aggressive: restructure control flow
    PARALLELIZE = "parallelize"
    SEQUENTIALIZE = "sequentialize"
    LOOP_UNROLL = "loop_unroll"
    CONDITIONAL_INJECT = "conditional_inject"
    # Radical: generate entirely new strategies
    STRATEGY_SYNTHESIS = "strategy_synthesis"
    # Meta: modify the mutation operators themselves
    META_MUTATION = "meta_mutation"


# ─── Strategy Genome ─────────────────────────────────────────────


class StrategyGenome:
    """A self-describing, self-modifiable agent strategy.

    The genome encodes everything the agent IS as manipulable data:
    - dispatch_tree: ISA AgentOp tree (what to execute)
    - parameters: numeric/string knobs (how to execute)
    - mutation_rates: per-mutation-type probabilities (how to evolve)
    - constraints: invariants that must survive mutation (safety rails)
    - lineage: evolutionary history

    This IS code-as-data. The genome can be:
    1. Serialized to JSON (frozen)
    2. Mutated (transformed while frozen)
    3. Compiled back to executable form (thawed)
    4. Compared against other genomes (fitness tournament)
    """

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
            MutationType.PARAMETER_DRIFT: 0.40,
            MutationType.SUBTREE_SWAP: 0.15,
            MutationType.NODE_INSERT: 0.10,
            MutationType.NODE_DELETE: 0.08,
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

    # ── Identity ──────────────────────────────────────────────

    @property
    def genome_hash(self) -> str:
        """Content-addressable hash of the genome (deterministic identity)."""
        if self._hash is None:
            # Hash content WITHOUT including the hash itself to avoid recursion
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

    # ── Serialization (code → data) ───────────────────────────

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

    # ── Cloning ───────────────────────────────────────────────

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

    # ── Fitness ────────────────────────────────────────────────

    def record_fitness(self, record: FitnessRecord) -> None:
        """Record a fitness measurement."""
        self.lineage.fitness_history.append(record)
        # Keep history bounded
        if len(self.lineage.fitness_history) > 100:
            self.lineage.fitness_history = self.lineage.fitness_history[-50:]

    # ── Introspection (reflect on self) ───────────────────────

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


# ─── Genome Mutator ──────────────────────────────────────────────


class GenomeMutator:
    """Applies mutations to StrategyGenomes.

    Each mutation type is a function: Genome → Genome.
    The mutator selects mutations stochastically based on the genome's
    own mutation_rates (which can themselves be mutated via META_MUTATION).

    This is the transform in quote-transform-eval:
    - quote: genome.to_dict()
    - TRANSFORM: mutator.mutate(genome)
    - eval: genome.compile()
    """

    # ── Dispatch table ────────────────────────────────────────

    _OPERATORS: dict[MutationType, str] = {
        MutationType.PARAMETER_DRIFT: "_mutate_parameter_drift",
        MutationType.SUBTREE_SWAP: "_mutate_subtree_swap",
        MutationType.NODE_INSERT: "_mutate_node_insert",
        MutationType.NODE_DELETE: "_mutate_node_delete",
        MutationType.PARALLELIZE: "_mutate_parallelize",
        MutationType.SEQUENTIALIZE: "_mutate_sequentialize",
        MutationType.LOOP_UNROLL: "_mutate_loop_unroll",
        MutationType.CONDITIONAL_INJECT: "_mutate_conditional_inject",
        MutationType.STRATEGY_SYNTHESIS: "_mutate_strategy_synthesis",
        MutationType.META_MUTATION: "_mutate_meta",
    }

    def mutate(
        self, genome: StrategyGenome, *, force_type: MutationType | None = None
    ) -> StrategyGenome:
        """Apply a single mutation to a cloned genome.

        Returns a NEW genome (the original is untouched).
        The mutation type is selected stochastically from the genome's
        own mutation_rates, OR forced via force_type.
        """
        child = genome.clone()
        child.lineage.generation += 1

        if force_type:
            mutation_type = force_type
        else:
            mutation_type = self._select_mutation_type(child)

        ast_mutation_types = {
            MutationType.SUBTREE_SWAP,
            MutationType.NODE_INSERT,
            MutationType.NODE_DELETE,
            MutationType.PARALLELIZE,
            MutationType.SEQUENTIALIZE,
            MutationType.LOOP_UNROLL,
            MutationType.CONDITIONAL_INJECT,
            MutationType.STRATEGY_SYNTHESIS,
        }

        if mutation_type in ast_mutation_types:
            try:
                import cortex_rs
                tree_json = json.dumps(child.dispatch_tree, default=str)
                new_tree_json = cortex_rs.GenomeMutatorRs.mutate_tree(
                    tree_json, mutation_type.value, child.lineage.generation
                )
                child.dispatch_tree = json.loads(new_tree_json)
                child.lineage.mutation_log.append(
                    f"gen={child.lineage.generation} type={mutation_type.value} [Rust]"
                )
                child._invalidate_hash()
            except Exception as e:
                logger.error("Rust AST mutation failed: %s", e)
        else:
            method_name = self._OPERATORS.get(mutation_type)
            if method_name and hasattr(self, method_name):
                getattr(self, method_name)(child)
                child.lineage.mutation_log.append(
                    f"gen={child.lineage.generation} type={mutation_type.value}"
                )
                child._invalidate_hash()
                logger.debug(
                    "GENOME MUTATION: %s on %s → %s (gen %d)",
                    mutation_type.value,
                    genome.genome_hash[:8],
                    child.genome_hash[:8],
                    child.lineage.generation,
                )
            else:
                logger.warning("Unknown mutation type: %s", mutation_type)

        return child

    def crossover(self, parent_a: StrategyGenome, parent_b: StrategyGenome) -> StrategyGenome:
        """Sexual recombination: merge traits from two parent genomes.

        Strategy: take dispatch_tree from the fitter parent,
        parameters from a uniform crossover of both.
        """
        if parent_a.lineage.avg_fitness >= parent_b.lineage.avg_fitness:
            fitter, weaker = parent_a, parent_b
        else:
            fitter, weaker = parent_b, parent_a

        child = fitter.clone()
        child.name = f"crossover_{fitter.name[:8]}x{weaker.name[:8]}"
        child.lineage.generation = max(fitter.lineage.generation, weaker.lineage.generation) + 1
        child.lineage.parent_hash = f"{fitter.genome_hash}x{weaker.genome_hash}"

        # Uniform crossover on parameters
        all_keys = set(fitter.parameters) | set(weaker.parameters)
        for key in all_keys:
            if random.random() > 0.5:
                if key in weaker.parameters:
                    child.parameters[key] = copy.deepcopy(weaker.parameters[key])

        # Blend mutation rates
        for mt in MutationType:
            rate_a = fitter.mutation_rates.get(mt, 0.0)
            rate_b = weaker.mutation_rates.get(mt, 0.0)
            child.mutation_rates[mt] = (rate_a + rate_b) / 2.0

        child._invalidate_hash()
        child.lineage.mutation_log.append("crossover")
        return child

    # ── Selection ─────────────────────────────────────────────

    def _select_mutation_type(self, genome: StrategyGenome) -> MutationType:
        """Roulette wheel selection weighted by genome's own mutation_rates."""
        types = list(MutationType)
        weights = [genome.mutation_rates.get(mt, 0.01) for mt in types]
        total = sum(weights)
        if total <= 0:
            return random.choice(types)
        normalized = [w / total for w in weights]
        return random.choices(types, weights=normalized, k=1)[0]

    # ── Mutation Operators ────────────────────────────────────

    def _mutate_parameter_drift(self, genome: StrategyGenome) -> None:
        """Gaussian drift on numeric parameters."""
        if not genome.parameters:
            genome.parameters["drift_seed"] = random.gauss(0.5, 0.1)
            return

        key = random.choice(list(genome.parameters))
        val = genome.parameters[key]
        if isinstance(val, int | float):
            sigma = abs(val) * 0.1 + 0.01
            genome.parameters[key] = val + random.gauss(0, sigma)
        elif isinstance(val, bool):
            genome.parameters[key] = not val
        elif isinstance(val, str):
            # Prefix mutation
            genome.parameters[key] = f"mutated_{val}"

    def _mutate_subtree_swap(self, genome: StrategyGenome) -> None:
        """Swap a random subtree with a new dispatch node."""
        tree = genome.dispatch_tree
        if isinstance(tree, str) or not isinstance(tree, dict):
            genome.dispatch_tree = dispatch(
                f"evolved_target_{random.randint(100, 999)}",
                {"source": "subtree_swap"},
            )
            return

        targets = dispatch_targets(tree)
        if targets:
            # Replace one target with a new one
            old_target = random.choice(targets)
            new_target = f"evolved_{old_target}_{genome.lineage.generation}"
            genome.dispatch_tree = self._replace_target(tree, old_target, new_target)

    def _mutate_node_insert(self, genome: StrategyGenome) -> None:
        """Insert a new node into the dispatch tree."""
        new_node = dispatch(
            f"injected_{random.randint(1000, 9999)}",
            {"gen": genome.lineage.generation, "type": "injected"},
        )
        tree = genome.dispatch_tree
        if isinstance(tree, str) or tree == noop():
            genome.dispatch_tree = new_node
        elif isinstance(tree, dict):
            # Wrap in a sequence with the new node
            if random.random() > 0.5:
                genome.dispatch_tree = seq(tree, new_node)
            else:
                genome.dispatch_tree = seq(new_node, tree)

    def _mutate_node_delete(self, genome: StrategyGenome) -> None:
        """Remove a random dispatch node from the tree."""
        targets = dispatch_targets(genome.dispatch_tree)
        if targets:
            target_to_remove = random.choice(targets)
            genome.dispatch_tree = self._remove_target(genome.dispatch_tree, target_to_remove)

    def _mutate_parallelize(self, genome: StrategyGenome) -> None:
        """Convert a Seq node to Par (parallelize sequential operations)."""
        tree = genome.dispatch_tree
        if isinstance(tree, dict) and "Seq" in tree:
            genome.dispatch_tree = {"Par": tree["Seq"]}

    def _mutate_sequentialize(self, genome: StrategyGenome) -> None:
        """Convert a Par node to Seq (sequentialize parallel operations)."""
        tree = genome.dispatch_tree
        if isinstance(tree, dict) and "Par" in tree:
            genome.dispatch_tree = {"Seq": tree["Par"]}

    def _mutate_loop_unroll(self, genome: StrategyGenome) -> None:
        """Unroll a Loop node into a Seq of repeated bodies."""
        tree = genome.dispatch_tree
        if isinstance(tree, dict) and "Loop" in tree:
            loop_data = tree["Loop"]
            count = loop_data.get("count", 1)
            body = loop_data.get("body", noop())
            if count <= 5:
                genome.dispatch_tree = seq(*[copy.deepcopy(body) for _ in range(count)])

    def _mutate_conditional_inject(self, genome: StrategyGenome) -> None:
        """Wrap the tree in a conditional guard."""
        genome.dispatch_tree = cond(
            Predicate.always(),
            then_branch=genome.dispatch_tree,
            else_branch=halt(error="conditional_guard_failed"),
        )

    def _mutate_strategy_synthesis(self, genome: StrategyGenome) -> None:
        """Generate an entirely new dispatch tree from scratch."""
        strategies = [
            # Strategy A: Fan-out parallel hunters
            par(
                dispatch("synth_alpha", {"mode": "scan"}, id=random.randint(100, 999)),
                dispatch("synth_beta", {"mode": "extract"}, id=random.randint(100, 999)),
                dispatch("synth_gamma", {"mode": "verify"}, id=random.randint(100, 999)),
            ),
            # Strategy B: Sequential pipeline
            seq(
                dispatch("synth_ingest", {"phase": 1}),
                dispatch("synth_process", {"phase": 2}),
                dispatch("synth_emit", {"phase": 3}),
            ),
            # Strategy C: Conditional branching
            cond(
                Predicate.always(),
                then_branch=seq(
                    dispatch("synth_primary", {}),
                    dispatch("synth_validate", {}),
                ),
                else_branch=dispatch("synth_fallback", {}),
            ),
            # Strategy D: Loop with guard
            seq(
                dispatch("synth_init", {}),
                loop_n(3, dispatch("synth_iterate", {"cycle": True})),
                dispatch("synth_finalize", {}),
            ),
        ]
        genome.dispatch_tree = random.choice(strategies)
        genome.parameters["synthesis_epoch"] = genome.lineage.generation

    def _mutate_meta(self, genome: StrategyGenome) -> None:
        """META-MUTATION: Modify the genome's own mutation rates.

        This is the core of L7: the mutation operator mutates itself.
        The genome's propensity to mutate in certain ways is itself
        subject to evolution.
        """
        mt = random.choice(list(MutationType))
        current_rate = genome.mutation_rates.get(mt, 0.05)
        # Gaussian perturbation of mutation rate
        delta = random.gauss(0, 0.05)
        new_rate = max(0.001, min(0.8, current_rate + delta))
        genome.mutation_rates[mt] = new_rate
        genome.lineage.mutation_log.append(
            f"META: {mt.value} rate {current_rate:.3f} → {new_rate:.3f}"
        )

    # ── Tree manipulation helpers ─────────────────────────────

    @staticmethod
    def _replace_target(tree: AgentOp, old_target: str, new_target: str) -> AgentOp:
        """Replace a dispatch target in the tree."""
        if isinstance(tree, str) or not isinstance(tree, dict):
            return tree

        result = {}
        for variant, data in tree.items():
            if variant == "Dispatch" and isinstance(data, dict):
                if data.get("target") == old_target:
                    result[variant] = {**data, "target": new_target}
                else:
                    result[variant] = data
            elif variant in ("Seq", "Par") and isinstance(data, list):
                result[variant] = [
                    GenomeMutator._replace_target(child, old_target, new_target) for child in data
                ]
            elif variant == "Cond" and isinstance(data, dict):
                result[variant] = {
                    "predicate": data.get("predicate"),
                    "then_branch": GenomeMutator._replace_target(
                        data.get("then_branch", {}), old_target, new_target
                    ),
                    "else_branch": GenomeMutator._replace_target(
                        data.get("else_branch", "Noop"), old_target, new_target
                    ),
                }
            elif variant == "Loop" and isinstance(data, dict):
                result[variant] = {
                    "count": data.get("count", 1),
                    "body": GenomeMutator._replace_target(
                        data.get("body", {}), old_target, new_target
                    ),
                }
            else:
                result[variant] = data
        return result

    @staticmethod
    def _remove_target(tree: AgentOp, target: str) -> AgentOp:
        """Remove a dispatch target from the tree, replacing with Noop."""
        if isinstance(tree, str) or not isinstance(tree, dict):
            return tree

        result = {}
        for variant, data in tree.items():
            if variant == "Dispatch" and isinstance(data, dict):
                if data.get("target") == target:
                    return "Noop"
                result[variant] = data
            elif variant in ("Seq", "Par") and isinstance(data, list):
                children = [GenomeMutator._remove_target(child, target) for child in data]
                children = [c for c in children if c != "Noop"]
                if not children:
                    return "Noop"
                result[variant] = children
            elif variant == "Cond" and isinstance(data, dict):
                result[variant] = {
                    "predicate": data.get("predicate"),
                    "then_branch": GenomeMutator._remove_target(
                        data.get("then_branch", {}), target
                    ),
                    "else_branch": GenomeMutator._remove_target(
                        data.get("else_branch", "Noop"), target
                    ),
                }
            elif variant == "Loop" and isinstance(data, dict):
                result[variant] = {
                    "count": data.get("count", 1),
                    "body": GenomeMutator._remove_target(data.get("body", {}), target),
                }
            else:
                result[variant] = data
        return result

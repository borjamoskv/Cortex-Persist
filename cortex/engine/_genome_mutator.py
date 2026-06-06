# [C5-REAL] Exergy-Maximized
"""GenomeMutator logic.

Reality Level: C5-REAL
"""

from __future__ import annotations

import copy
import json
import logging
import random

from cortex.engine._genome_tree_helper import remove_target, replace_target
from cortex.engine._genome_types import MutationType, StrategyGenome
from cortex.isa.builder import (
    Predicate,
    cond,
    dispatch,
    dispatch_targets,
    halt,
    loop_n,
    noop,
    par,
    seq,
)

logger = logging.getLogger("cortex.engine.genome")


class GenomeMutator:
    """Applies mutations to StrategyGenomes."""

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
        """Apply a single mutation to a cloned genome."""
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
                new_tree_json = cortex_rs.GenomeMutatorRs.mutate_tree(  # pyright: ignore[reportAttributeAccessIssue]
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
        """Sexual recombination: merge traits from two parent genomes."""
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

    def _select_mutation_type(self, genome: StrategyGenome) -> MutationType:
        """Roulette wheel selection weighted by genome's own mutation_rates."""
        types = list(MutationType)
        weights = [genome.mutation_rates.get(mt, 0.01) for mt in types]
        total = sum(weights)
        if total <= 0:
            return random.choice(types)
        normalized = [w / total for w in weights]
        return random.choices(types, weights=normalized, k=1)[0]

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
            old_target = random.choice(targets)
            new_target = f"evolved_{old_target}_{genome.lineage.generation}"
            genome.dispatch_tree = replace_target(tree, old_target, new_target)

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
            if random.random() > 0.5:
                genome.dispatch_tree = seq(tree, new_node)
            else:
                genome.dispatch_tree = seq(new_node, tree)

    def _mutate_node_delete(self, genome: StrategyGenome) -> None:
        """Remove a random dispatch node from the tree."""
        targets = dispatch_targets(genome.dispatch_tree)
        if targets:
            target_to_remove = random.choice(targets)
            genome.dispatch_tree = remove_target(genome.dispatch_tree, target_to_remove)

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
            par(
                dispatch("synth_alpha", {"mode": "scan"}, id=random.randint(100, 999)),
                dispatch("synth_beta", {"mode": "extract"}, id=random.randint(100, 999)),
                dispatch("synth_gamma", {"mode": "verify"}, id=random.randint(100, 999)),
            ),
            seq(
                dispatch("synth_ingest", {"phase": 1}),
                dispatch("synth_process", {"phase": 2}),
                dispatch("synth_emit", {"phase": 3}),
            ),
            cond(
                Predicate.always(),
                then_branch=seq(
                    dispatch("synth_primary", {}),
                    dispatch("synth_validate", {}),
                ),
                else_branch=dispatch("synth_fallback", {}),
            ),
            seq(
                dispatch("synth_init", {}),
                loop_n(3, dispatch("synth_iterate", {"cycle": True})),
                dispatch("synth_finalize", {}),
            ),
        ]
        genome.dispatch_tree = random.choice(strategies)
        genome.parameters["synthesis_epoch"] = genome.lineage.generation

    def _mutate_meta(self, genome: StrategyGenome) -> None:
        """META-MUTATION: Modify the genome's own mutation rates."""
        mt = random.choice(list(MutationType))
        current_rate = genome.mutation_rates.get(mt, 0.05)
        delta = random.gauss(0, 0.05)
        new_rate = max(0.001, min(0.8, current_rate + delta))
        genome.mutation_rates[mt] = new_rate
        genome.lineage.mutation_log.append(
            f"META: {mt.value} rate {current_rate:.3f} → {new_rate:.3f}"
        )

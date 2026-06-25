# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import copy
import logging
import random
import time
from typing import Any

from legacy_research.sica.strategy import Heuristic, SearchStrategy, StrategyGenome

from .types import GeneFragment

logger = logging.getLogger("cortex.sica.colony.genetics")


def _interleave(a: list[str], b: list[str]) -> list[str]:
    """Interleave two lists."""
    result: list[str] = []
    i, j = 0, 0
    while i < len(a) or j < len(b):
        if i < len(a):
            result.append(a[i])
            i += 1
        if j < len(b):
            result.append(b[j])
            j += 1
    return result


class GenePool:
    """Colony-wide repository of shared genetic material.

    Agents DONATE successful genome fragments.
    Other agents ADOPT fragments that match their needs.
    The pool tracks which fragments are successful when adopted,
    creating a colony-level selection pressure.
    """

    def __init__(self, max_fragments: int = 100) -> None:
        self._fragments: dict[str, GeneFragment] = {}
        self._max_fragments = max_fragments
        self._donation_log: list[dict[str, Any]] = []

    @property
    def size(self) -> int:
        return len(self._fragments)

    @property
    def fragments(self) -> list[GeneFragment]:
        return list(self._fragments.values())

    def donate(
        self,
        agent_id: str,
        strategy: SearchStrategy,
        min_fitness: float = 0.6,
    ) -> list[str]:
        """Donate successful genome fragments to the pool.

        Only donates fragments with fitness above threshold.
        Returns list of donated fragment IDs.
        """
        donated: list[str] = []
        genome = strategy.genome

        # Donate individual high-fitness heuristics
        for h in genome.heuristics:
            if h.fitness >= min_fitness and h.activation_count >= 3:
                fid = f"h:{agent_id}:{h.name}:g{genome.generation}"
                self._fragments[fid] = GeneFragment(
                    fragment_id=fid,
                    donor_agent=agent_id,
                    donor_generation=genome.generation,
                    fragment_type="heuristic",
                    payload={
                        "name": h.name,
                        "description": h.description,
                        "weight": h.weight,
                    },
                    fitness_at_donation=h.fitness,
                )
                donated.append(fid)

        # Donate tool ordering if overall fitness is high
        if strategy.current_fitness >= min_fitness:
            fid = f"tools:{agent_id}:g{genome.generation}"
            self._fragments[fid] = GeneFragment(
                fragment_id=fid,
                donor_agent=agent_id,
                donor_generation=genome.generation,
                fragment_type="tool_order",
                payload={"tool_priority": list(genome.tool_priority)},
                fitness_at_donation=strategy.current_fitness,
            )
            donated.append(fid)

            # Donate full genome snapshot
            fid = f"genome:{agent_id}:g{genome.generation}"
            self._fragments[fid] = GeneFragment(
                fragment_id=fid,
                donor_agent=agent_id,
                donor_generation=genome.generation,
                fragment_type="genome",
                payload=genome.to_dict(),
                fitness_at_donation=strategy.current_fitness,
            )
            donated.append(fid)

        # Evict low-value fragments if pool is full
        self._evict_if_full()

        if donated:
            self._donation_log.append(
                {
                    "agent": agent_id,
                    "fragments": donated,
                    "time": time.monotonic(),
                }
            )
            logger.info(
                "GenePool: %s donated %d fragments (pool size=%d)",
                agent_id,
                len(donated),
                self.size,
            )

        return donated

    def adopt(
        self,
        agent_id: str,
        strategy: SearchStrategy,
        max_adoptions: int = 3,
    ) -> list[GeneFragment]:
        """Adopt the best fragments from the pool."""
        existing_names = {h.name for h in strategy.genome.heuristics}
        candidates = self._get_adoptable_candidates(agent_id, existing_names)

        adopted: list[GeneFragment] = []
        donors_seen: set[str] = set()

        for frag in candidates:
            if len(adopted) >= max_adoptions:
                break
            if frag.donor_agent in donors_seen and len(adopted) > 1:
                continue
            if self._apply_fragment(frag, strategy):
                frag.adoption_count += 1
                adopted.append(frag)
                donors_seen.add(frag.donor_agent)

        if adopted:
            logger.info(
                "GenePool: %s adopted %d fragments: %s",
                agent_id,
                len(adopted),
                [f.fragment_id for f in adopted],
            )
        return adopted

    def _get_adoptable_candidates(
        self, agent_id: str, existing_names: set[str]
    ) -> list[GeneFragment]:
        candidates = [
            f
            for f in self._fragments.values()
            if f.donor_agent != agent_id
            and (f.fragment_type != "heuristic" or f.payload.get("name") not in existing_names)
        ]
        candidates.sort(key=lambda f: f.value_score, reverse=True)
        return candidates

    def report_adoption_outcome(
        self,
        fragment_id: str,
        success: bool,
    ) -> None:
        """Report whether an adopted fragment improved performance."""
        if fragment_id in self._fragments:
            if success:
                self._fragments[fragment_id].adoption_success_count += 1

    def _apply_fragment(
        self,
        fragment: GeneFragment,
        strategy: SearchStrategy,
    ) -> bool:
        """Apply a gene fragment to a strategy."""
        if fragment.fragment_type == "heuristic":
            name = fragment.payload["name"]
            desc = fragment.payload.get("description", "")
            base_weight = fragment.payload.get("weight", 0.5)

            # Integrate Heuristic drift logic during adoption
            drift = random.uniform(-0.1, 0.1) if random.random() < 0.2 else 0.0
            mutated_weight = max(0.1, min(1.0, base_weight + drift))

            h = Heuristic(name=name, description=desc, weight=mutated_weight)
            strategy.mutate_inject(
                h,
                reason=f"colony adoption from {fragment.donor_agent} (drift {drift:+.2f})",
            )
            return True

        if fragment.fragment_type == "tool_order":
            new_order = fragment.payload.get("tool_priority", [])
            if new_order:
                # Merge: add new tools, keep existing order for known tools
                existing = set(strategy.genome.tool_priority)
                for tool in new_order:
                    if tool not in existing:
                        strategy.genome.tool_priority.append(tool)
                return True

        elif fragment.fragment_type == "exploration_rate":
            rate = fragment.payload.get("exploration_rate")
            if rate is not None:
                # Blend: average with current rate
                current = strategy.genome.exploration_rate
                blended = (current + rate) / 2
                strategy.mutate_exploration_rate(
                    blended,
                    reason=f"colony adoption from {fragment.donor_agent}",
                )
                return True

        return False

    def _evict_if_full(self) -> None:
        """Remove lowest-value fragments when pool exceeds capacity."""
        while len(self._fragments) > self._max_fragments:
            worst = min(self._fragments.values(), key=lambda f: f.value_score)
            del self._fragments[worst.fragment_id]


class GenomeCrossover:
    """Combine the best parts of two parent genomes.

    Like biological sexual reproduction:
    - Take high-fitness heuristics from both parents
    - Blend exploration rates
    - Merge tool priorities
    - Create a child genome that inherits the best of both
    """

    def crossover(
        self,
        parent_a: StrategyGenome,
        parent_b: StrategyGenome,
    ) -> StrategyGenome:
        """Create a child genome from two parents."""
        all_heuristics = self._merge_heuristics(parent_a, parent_b)

        # Apply structural drift to inherited heuristics
        for h in all_heuristics.values():
            if random.random() < 0.15:  # 15% chance to mutate weight
                drift = random.uniform(-0.15, 0.15)
                h.weight = max(0.1, min(1.0, h.weight + drift))

        # Blend exploration rates
        er = (parent_a.exploration_rate + parent_b.exploration_rate) / 2

        # Merge tool priorities (interleave, deduplicate)
        tools = self._merge_tools(parent_a, parent_b)

        # Decomposition: take the average
        decomp = (parent_a.decomposition_depth + parent_b.decomposition_depth) // 2

        child = StrategyGenome(
            heuristics=list(all_heuristics.values()),
            tool_priority=tools,
            decomposition_depth=decomp,
            exploration_rate=er,
            error_recovery_mode=parent_a.error_recovery_mode,
            generation=max(parent_a.generation, parent_b.generation) + 1,
            parent_hash=f"{parent_a.genome_hash}×{parent_b.genome_hash}",
        )

        logger.info(
            "Crossover: %s × %s → %s (heuristics=%d, er=%.2f)",
            parent_a.genome_hash,
            parent_b.genome_hash,
            child.genome_hash,
            len(child.heuristics),
            child.exploration_rate,
        )
        return child

    def _merge_heuristics(
        self, parent_a: StrategyGenome, parent_b: StrategyGenome
    ) -> dict[str, Heuristic]:
        all_heuristics: dict[str, Heuristic] = {}
        for h in parent_a.heuristics:
            if h.fitness > 0.4:
                all_heuristics[h.name] = copy.deepcopy(h)

        for h in parent_b.heuristics:
            if h.fitness > 0.4:
                if h.name in all_heuristics:
                    if h.fitness > all_heuristics[h.name].fitness:
                        all_heuristics[h.name] = copy.deepcopy(h)
                else:
                    all_heuristics[h.name] = copy.deepcopy(h)
        return all_heuristics

    def _merge_tools(self, parent_a: StrategyGenome, parent_b: StrategyGenome) -> list[str]:
        tools: list[str] = []
        seen: set[str] = set()
        for t in _interleave(parent_a.tool_priority, parent_b.tool_priority):
            if t not in seen:
                tools.append(t)
                seen.add(t)
        return tools


class GenomeMutator:
    """Spontaneous point-mutation engine (Gamma Ray Exposure).

    Unlike crossover or adoption, this introduces entirely novel variance
    into a single genome without requiring external donors. It prevents
    the swarm from converging entirely on a local optimum.
    """

    LATENT_HEURISTICS = [
        Heuristic(
            name="lateral_thinking",
            description="If blocked, abandon the current context entirely and restart from a new angle.",
            weight=0.5,
        ),
        Heuristic(
            name="simplification_bias",
            description="Aggressively reduce the scope of the problem to the smallest testable unit.",
            weight=0.6,
        ),
        Heuristic(
            name="adversarial_validation",
            description="Write tests designed specifically to break the proposed solution.",
            weight=0.7,
        ),
        Heuristic(
            name="memory_archaeology",
            description="Force a deep scan of the semantic ledger before attempting a novel solution.",
            weight=0.5,
        ),
    ]

    def mutate(self, genome: StrategyGenome, mutation_rate: float = 0.05) -> StrategyGenome:
        """Apply spontaneous point mutations to a genome.

        Args:
            genome: The target genome to mutate.
            mutation_rate: The baseline probability of a mutation event.
        """
        mutated = copy.deepcopy(genome)
        mutated_flag = False

        # 1. Point Drift on existing heuristics
        for h in mutated.heuristics:
            if random.random() < mutation_rate:
                # Spontaneous heavy drift
                drift = random.uniform(-0.3, 0.3)
                h.weight = max(0.1, min(1.0, h.weight + drift))
                mutated_flag = True

        # 2. Spontaneous Injection (Innovation)
        if random.random() < (mutation_rate * 0.5):
            novel = copy.deepcopy(random.choice(self.LATENT_HEURISTICS))
            # Inject only if it doesn't already exist
            if not any(h.name == novel.name for h in mutated.heuristics):
                mutated.heuristics.append(novel)
                mutated_flag = True

        # 3. Gene Deletion (Pruning stagnated sequences)
        if len(mutated.heuristics) > 3 and random.random() < mutation_rate:
            # Drop the lowest weight heuristic
            worst = min(mutated.heuristics, key=lambda h: h.weight)
            mutated.heuristics.remove(worst)
            mutated_flag = True

        # 4. Exploration Rate shift
        if random.random() < mutation_rate:
            shift = random.uniform(-0.2, 0.2)
            mutated.exploration_rate = max(0.1, min(0.9, mutated.exploration_rate + shift))
            mutated_flag = True

        if mutated_flag:
            mutated.generation += 1
            mutated.parent_hash = f"mut({genome.genome_hash})"
            logger.info(
                "Spontaneous Mutation: %s → %s",
                genome.genome_hash,
                mutated.genome_hash,
            )

        return mutated

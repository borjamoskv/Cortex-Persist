"""SICA Colony — Horizontal Gene Transfer & Emergent Specialization.

Single agents evolve. Colonies ACCELERATE evolution.

Biological parallel: bacteria share genetic material via
horizontal gene transfer (HGT), enabling rapid adaptation
across the colony without each individual having to
independently evolve the same solution.

SICA Colony enables:
  1. GENOME SHARING: agents publish successful genome fragments
  2. TOURNAMENT: genomes compete on shared benchmarks
  3. SPECIALIZATION: agents differentiate into roles based on fitness
  4. CROSSOVER: combine the best parts of different genomes
  5. MIGRATION: move successful heuristics between agents

Architecture:
  ┌────────┐   ┌────────┐   ┌────────┐
  │Agent-A │   │Agent-B │   │Agent-C │
  │gen=42  │   │gen=18  │   │gen=31  │
  │search↑ │   │deploy↑ │   │verify↑ │
  └───┬────┘   └───┬────┘   └───┬────┘
      │            │            │
      └────────────┼────────────┘
                   │
          ┌────────┴────────┐
          │   GENE POOL     │
          │ shared fragments│
          │ tournament arena│
          │ specialization  │
          └─────────────────┘
"""

from __future__ import annotations

import copy
import logging
import random
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from cortex.sica.strategy import (
    Heuristic,
    SearchStrategy,
    StrategyGenome,
    StrategyMutation,
    MutationType,
)

logger = logging.getLogger("cortex.sica.colony")


# ═══════════════════════════════════════════════════════════════════
# GENE POOL — Shared fragment repository
# ═══════════════════════════════════════════════════════════════════


@dataclass
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
        """Adopt the best fragments from the pool.

        Selection criteria:
        1. Don't adopt your own donations
        2. Don't adopt heuristics you already have
        3. Prefer high value_score fragments
        4. Prefer fragments from different donors (diversity)

        Returns the fragments that were adopted.
        """
        existing_names = {h.name for h in strategy.genome.heuristics}
        candidates = [f for f in self._fragments.values() if f.donor_agent != agent_id]

        # Filter heuristics we already have
        candidates = [
            f
            for f in candidates
            if f.fragment_type != "heuristic" or f.payload.get("name") not in existing_names
        ]

        # Sort by value score
        candidates.sort(key=lambda f: f.value_score, reverse=True)

        adopted: list[GeneFragment] = []
        donors_seen: set[str] = set()

        for frag in candidates:
            if len(adopted) >= max_adoptions:
                break

            # Prefer diversity: don't adopt too many from same donor
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
            weight = fragment.payload.get("weight", 0.5)
            h = Heuristic(name=name, description=desc, weight=weight)
            strategy.mutate_inject(
                h,
                reason=f"colony adoption from {fragment.donor_agent}",
            )
            return True

        elif fragment.fragment_type == "tool_order":
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


# ═══════════════════════════════════════════════════════════════════
# TOURNAMENT — Competitive genome evaluation
# ═══════════════════════════════════════════════════════════════════


@dataclass
class TournamentResult:
    """Result of a genome tournament."""

    winner: str  # agent_id
    rankings: list[tuple[str, float]]  # [(agent_id, score)]
    selection_pressure: float  # How much the winner dominated


class Tournament:
    """Competitive evaluation of genomes.

    Agents submit their genomes, which are evaluated against
    a shared benchmark. The winner's genome fragments get
    promoted in the gene pool.
    """

    def __init__(self) -> None:
        self._results_history: list[TournamentResult] = []

    @property
    def history(self) -> list[TournamentResult]:
        return list(self._results_history)

    def compete(
        self,
        entries: dict[str, SearchStrategy],
    ) -> TournamentResult:
        """Run a tournament between agent strategies.

        Evaluation criteria:
        1. Current fitness (40%)
        2. Genome diversity / heuristic count (20%)
        3. Exploration-exploitation balance (20%)
        4. Mutation efficiency (20%)
        """
        scores: list[tuple[str, float]] = []

        for agent_id, strategy in entries.items():
            genome = strategy.genome
            fitness_score = strategy.current_fitness * 0.4

            # Diversity: number of active heuristics (more = better, up to a point)
            n_active = len(genome.active_heuristics)
            diversity_score = min(1.0, n_active / 8) * 0.2

            # Exploration balance: penalize extremes
            er = genome.exploration_rate
            balance_score = (1.0 - abs(er - 0.3) * 2) * 0.2

            # Mutation efficiency: ratio of positive mutations
            mutations = strategy.mutation_log
            if mutations:
                positive = sum(
                    1 for m in mutations if m.fitness_delta is not None and m.fitness_delta > 0
                )
                efficiency = positive / len(mutations)
            else:
                efficiency = 0.5
            efficiency_score = efficiency * 0.2

            total = fitness_score + diversity_score + balance_score + efficiency_score
            scores.append((agent_id, round(total, 4)))

        scores.sort(key=lambda x: x[1], reverse=True)
        winner = scores[0][0]
        winner_score = scores[0][1]
        avg_score = sum(s for _, s in scores) / len(scores)
        selection_pressure = winner_score - avg_score

        result = TournamentResult(
            winner=winner,
            rankings=scores,
            selection_pressure=round(selection_pressure, 4),
        )
        self._results_history.append(result)

        logger.info(
            "Tournament: winner=%s (%.3f), pressure=%.3f",
            winner,
            winner_score,
            selection_pressure,
        )
        return result


# ═══════════════════════════════════════════════════════════════════
# GENOME CROSSOVER — Sexual reproduction for strategies
# ═══════════════════════════════════════════════════════════════════


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
        """Create a child genome from two parents.

        Selection rule: for each heuristic present in either parent,
        include it if its fitness > 0.5, using the higher-weight version.
        """
        # Collect all heuristics from both parents
        all_heuristics: dict[str, Heuristic] = {}

        for h in parent_a.heuristics:
            if h.fitness > 0.4:
                all_heuristics[h.name] = copy.deepcopy(h)

        for h in parent_b.heuristics:
            if h.fitness > 0.4:
                if h.name in all_heuristics:
                    # Take the one with higher fitness
                    if h.fitness > all_heuristics[h.name].fitness:
                        all_heuristics[h.name] = copy.deepcopy(h)
                else:
                    all_heuristics[h.name] = copy.deepcopy(h)

        # Blend exploration rates
        er = (parent_a.exploration_rate + parent_b.exploration_rate) / 2

        # Merge tool priorities (interleave, deduplicate)
        tools: list[str] = []
        seen: set[str] = set()
        for t in _interleave(parent_a.tool_priority, parent_b.tool_priority):
            if t not in seen:
                tools.append(t)
                seen.add(t)

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


# ═══════════════════════════════════════════════════════════════════
# SPECIALIZATION — Emergent role differentiation
# ═══════════════════════════════════════════════════════════════════


@dataclass
class AgentSpecialization:
    """Detected specialization of an agent."""

    agent_id: str
    primary_role: str  # "searcher" | "deployer" | "verifier" | "generalist"
    role_confidence: float
    dominant_tools: list[str]
    dominant_heuristics: list[str]
    fitness_in_role: float


class SpecializationDetector:
    """Detect emergent specialization in a colony of agents.

    By analyzing which agents perform best with which tools
    and task types, we can assign roles and route tasks
    to the most specialized agent.
    """

    def detect(
        self,
        agents: dict[str, SearchStrategy],
    ) -> dict[str, AgentSpecialization]:
        """Analyze all agents and detect their specializations."""
        specializations: dict[str, AgentSpecialization] = {}

        for agent_id, strategy in agents.items():
            genome = strategy.genome

            # Find dominant heuristics (top by weight)
            sorted_h = sorted(
                genome.active_heuristics,
                key=lambda h: h.weight,
                reverse=True,
            )
            dominant_h = [h.name for h in sorted_h[:3]]

            # Find dominant tools
            dominant_tools = genome.tool_priority[:3]

            # Classify role based on dominant heuristics
            role, confidence = self._classify_role(dominant_h, dominant_tools, genome)

            specializations[agent_id] = AgentSpecialization(
                agent_id=agent_id,
                primary_role=role,
                role_confidence=confidence,
                dominant_tools=dominant_tools,
                dominant_heuristics=dominant_h,
                fitness_in_role=round(strategy.current_fitness, 3),
            )

        return specializations

    def recommend_routing(
        self,
        task_type: str,
        specializations: dict[str, AgentSpecialization],
    ) -> list[tuple[str, float]]:
        """Recommend which agent should handle a given task type.

        Returns list of (agent_id, suitability_score) sorted desc.
        """
        task_role_map = {
            "search": "searcher",
            "find": "searcher",
            "deploy": "deployer",
            "build": "deployer",
            "test": "verifier",
            "verify": "verifier",
            "check": "verifier",
        }

        ideal_role = task_role_map.get(task_type, "generalist")

        scored: list[tuple[str, float]] = []
        for agent_id, spec in specializations.items():
            if spec.primary_role == ideal_role:
                score = spec.fitness_in_role * spec.role_confidence
            elif spec.primary_role == "generalist":
                score = spec.fitness_in_role * 0.7
            else:
                score = spec.fitness_in_role * 0.3
            scored.append((agent_id, round(score, 3)))

        return sorted(scored, key=lambda x: x[1], reverse=True)

    def _classify_role(
        self,
        dominant_heuristics: list[str],
        dominant_tools: list[str],
        genome: StrategyGenome,
    ) -> tuple[str, float]:
        """Classify an agent's role from its genome signature."""
        search_signals = {"search", "grep", "find", "read", "analyze"}
        deploy_signals = {"deploy", "build", "mutate", "write", "create"}
        verify_signals = {"verify", "test", "check", "validate", "audit"}

        all_signals = set(dominant_tools) | set(dominant_heuristics)

        scores = {
            "searcher": len(all_signals & search_signals),
            "deployer": len(all_signals & deploy_signals),
            "verifier": len(all_signals & verify_signals),
        }

        best_role = max(scores, key=scores.get)  # type: ignore[arg-type]
        best_score = scores[best_role]

        if best_score == 0:
            return "generalist", 0.5

        total = sum(scores.values())
        confidence = best_score / total if total > 0 else 0.5

        return best_role, round(confidence, 3)


# ═══════════════════════════════════════════════════════════════════
# COLONY COORDINATOR — Orchestrates all colony operations
# ═══════════════════════════════════════════════════════════════════


class Colony:
    """Top-level colony coordinator.

    Manages the gene pool, tournaments, crossover, and
    specialization detection for a group of SICA agents.
    """

    def __init__(self, max_pool_size: int = 100) -> None:
        self.gene_pool = GenePool(max_fragments=max_pool_size)
        self.tournament = Tournament()
        self.crossover = GenomeCrossover()
        self.specialization = SpecializationDetector()
        self._agents: dict[str, SearchStrategy] = {}

    def register(self, agent_id: str, strategy: SearchStrategy) -> None:
        """Register an agent with the colony."""
        self._agents[agent_id] = strategy

    def unregister(self, agent_id: str) -> None:
        """Remove an agent from the colony."""
        self._agents.pop(agent_id, None)

    @property
    def population(self) -> int:
        return len(self._agents)

    def evolve_cycle(self) -> dict[str, Any]:
        """Run one colony evolution cycle:
        1. All agents donate to gene pool
        2. All agents adopt from gene pool
        3. Run tournament
        4. Detect specializations
        5. Top agents breed via crossover

        Returns a report of what happened.
        """
        report: dict[str, Any] = {"cycle": "evolve", "agents": self.population}

        if self.population < 2:
            report["skipped"] = "need >= 2 agents"
            return report

        # 1. Donations
        total_donated = 0
        for agent_id, strategy in self._agents.items():
            donated = self.gene_pool.donate(agent_id, strategy)
            total_donated += len(donated)
        report["donated"] = total_donated

        # 2. Adoptions
        total_adopted = 0
        for agent_id, strategy in self._agents.items():
            adopted = self.gene_pool.adopt(agent_id, strategy)
            total_adopted += len(adopted)
        report["adopted"] = total_adopted

        # 3. Tournament
        result = self.tournament.compete(self._agents)
        report["tournament_winner"] = result.winner
        report["selection_pressure"] = result.selection_pressure

        # 4. Specialization
        specs = self.specialization.detect(self._agents)
        report["specializations"] = {
            k: {"role": v.primary_role, "confidence": v.role_confidence} for k, v in specs.items()
        }

        # 5. Crossover: breed the top 2
        if len(result.rankings) >= 2:
            parent_a_id = result.rankings[0][0]
            parent_b_id = result.rankings[1][0]
            parent_a = self._agents[parent_a_id].genome
            parent_b = self._agents[parent_b_id].genome
            child = self.crossover.crossover(parent_a, parent_b)
            report["crossover"] = {
                "parents": [parent_a_id, parent_b_id],
                "child_hash": child.genome_hash,
                "child_heuristics": len(child.heuristics),
            }
            # Inject child genome into gene pool
            child_strategy = SearchStrategy(child)
            self.gene_pool.donate(
                f"crossover:{parent_a_id}x{parent_b_id}", child_strategy, min_fitness=0.0
            )

        logger.info("Colony evolve cycle: %s", report)
        return report

    def introspect(self) -> dict[str, Any]:
        """Full colony state."""
        return {
            "population": self.population,
            "gene_pool_size": self.gene_pool.size,
            "tournament_count": len(self.tournament.history),
            "agents": list(self._agents.keys()),
            "specializations": {
                k: v.primary_role for k, v in self.specialization.detect(self._agents).items()
            }
            if self.population > 0
            else {},
        }


# ── Helpers ──────────────────────────────────────────────────────


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

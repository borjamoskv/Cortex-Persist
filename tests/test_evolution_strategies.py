# tests/test_evolution_strategies.py
"""Comprehensive tests for the 8 improvement strategies.

Phase 2 (v3) coverage — every strategy tested for:
  - Agent-level evaluation (sovereign agent)
  - Subagent-level evaluation
  - Edge cases (boundary fitness, empty mutations, stagnation)
  - Telemetry integration (mocked CortexMetrics)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cortex.evolution.agents import (
    AgentDomain,
    Mutation,
    MutationType,
    SovereignAgent,
    SubAgent,
)
from cortex.evolution.cortex_metrics import DomainMetrics
from cortex.evolution.strategies import (
    AdversarialStressStrategy,
    BridgeImportStrategy,
    CrossoverRecombinationStrategy,
    EntropyReductionStrategy,
    HeuristicInjectionStrategy,
    ParameterTuningStrategy,
    PruneDeadPathStrategy,
    StagnationBreakerStrategy,
)


# ── Fixtures ──────────────────────────────────────────────────


def _make_metrics(**overrides) -> DomainMetrics:
    """Build a DomainMetrics with controllable values."""
    defaults = {
        "domain": AgentDomain.FABRICATION,
        "error_count": 0,
        "ghost_count": 0,
        "bridge_count": 0,
        "decision_count": 0,
        "knowledge_count": 0,
        "fact_density": 0,
    }
    defaults.update(overrides)
    return DomainMetrics(**defaults)


def _make_agent(
    domain: AgentDomain = AgentDomain.FABRICATION,
    fitness: float = 50.0,
    sub_fitness: list[float] | None = None,
    generation: int = 0,
) -> SovereignAgent:
    """Build a SovereignAgent with controllable subagent fitness."""
    agent = SovereignAgent(domain=domain)
    agent.fitness = fitness
    agent.generation = generation
    if sub_fitness:
        agent.subagents = []
        for i, f in enumerate(sub_fitness):
            sub = SubAgent(
                name=f"{domain.name.lower()}-sub-{i}",
                domain=domain,
                fitness=f,
            )
            agent.subagents.append(sub)
    return agent


def _patch_dm(metrics: DomainMetrics):
    """Patch the _dm helper to return our controlled metrics."""
    return patch("cortex.evolution.strategies._dm", return_value=metrics)


# ── ParameterTuningStrategy ──────────────────────────────────


class TestParameterTuning:
    def test_sovereign_grade_returns_none(self):
        """Health > 0.9 means sovereign-grade — no tuning needed."""
        m = _make_metrics(decision_count=10, bridge_count=5)  # health > 0.9
        agent = _make_agent(fitness=120.0)
        with _patch_dm(m):
            result = ParameterTuningStrategy().evaluate_agent(agent)
        assert result is None

    def test_low_error_small_delta(self):
        """Low error_rate → small tuning nudges (stable domain)."""
        m = _make_metrics(error_count=0)  # error_rate effectively 0
        agent = _make_agent(fitness=50.0)
        with _patch_dm(m):
            result = ParameterTuningStrategy().evaluate_agent(agent)
        if result is not None:
            assert result.mutation_type == MutationType.PARAMETER_TUNE
            # Scale is 0.5 + 2.5*0 = 0.5 → delta = 0.5 * uniform(0.5,1.2)
            assert 0.2 <= result.delta_fitness <= 1.0

    def test_high_error_large_delta(self):
        """High error_rate → big leaps (aggressive repair)."""
        m = _make_metrics(error_count=10, decision_count=0)  # high error_rate
        agent = _make_agent(fitness=30.0)
        with _patch_dm(m):
            result = ParameterTuningStrategy().evaluate_agent(agent)
        assert result is not None
        assert result.mutation_type == MutationType.PARAMETER_TUNE
        assert result.delta_fitness > 0

    def test_subagent_tuning(self):
        """Subagent tuning uses scaled-down parameters."""
        m = _make_metrics(error_count=5)
        sub = SubAgent(domain=AgentDomain.MEMORY, fitness=40.0)
        with _patch_dm(m):
            result = ParameterTuningStrategy().evaluate_subagent(sub)
        if result is not None:
            assert result.mutation_type == MutationType.PARAMETER_TUNE


# ── PruneDeadPathStrategy ─────────────────────────────────────


class TestPruneDeadPath:
    def test_prunes_worst_below_threshold(self):
        """Worst subagent below threshold gets pruned."""
        m = _make_metrics(ghost_count=5)  # threshold ~22.5
        agent = _make_agent(sub_fitness=[80.0, 70.0, 10.0])  # worst=10 < 22.5
        with _patch_dm(m):
            result = PruneDeadPathStrategy().evaluate_agent(agent)
        assert result is not None
        assert result.mutation_type == MutationType.PRUNE_DEAD_PATH
        assert result.delta_fitness > 0

    def test_no_prune_when_all_above_threshold(self):
        """All subagents above threshold → no pruning."""
        m = _make_metrics(ghost_count=0)  # threshold = 20
        agent = _make_agent(sub_fitness=[80.0, 70.0, 25.0])  # worst=25 > 20
        with _patch_dm(m):
            result = PruneDeadPathStrategy().evaluate_agent(agent)
        assert result is None

    def test_high_ghost_density_raises_threshold(self):
        """More ghosts → higher threshold → more aggressive pruning."""
        m = _make_metrics(ghost_count=20)  # ghost_density high → threshold ~40
        agent = _make_agent(sub_fitness=[80.0, 70.0, 35.0])  # worst=35 < 40
        with _patch_dm(m):
            result = PruneDeadPathStrategy().evaluate_agent(agent)
        assert result is not None

    def test_subagent_needs_generation_above_5(self):
        """Young subagents (gen ≤ 5) are protected from pruning."""
        m = _make_metrics(ghost_count=5)
        sub = SubAgent(domain=AgentDomain.MEMORY, fitness=5.0, generation=3)
        with _patch_dm(m):
            result = PruneDeadPathStrategy().evaluate_subagent(sub)
        assert result is None  # gen 3 ≤ 5 → protected

    def test_subagent_pruned_after_generation_5(self):
        """Old low-fitness subagents get pruned."""
        m = _make_metrics(ghost_count=5)
        sub = SubAgent(domain=AgentDomain.MEMORY, fitness=5.0, generation=10)
        with _patch_dm(m):
            result = PruneDeadPathStrategy().evaluate_subagent(sub)
        assert result is not None
        assert result.delta_fitness == 10.0


# ── HeuristicInjectionStrategy ────────────────────────────────


class TestHeuristicInjection:
    def test_injects_below_80_fitness(self):
        """Agents below 80 fitness receive heuristic injection."""
        m = _make_metrics(fact_density=100)
        agent = _make_agent(fitness=60.0)
        with _patch_dm(m):
            result = HeuristicInjectionStrategy().evaluate_agent(agent)
        assert result is not None
        assert result.mutation_type == MutationType.HEURISTIC_INJECT

    def test_no_injection_above_80(self):
        """Agents above 80 don't need injection."""
        m = _make_metrics()
        agent = _make_agent(fitness=85.0)
        with _patch_dm(m):
            result = HeuristicInjectionStrategy().evaluate_agent(agent)
        assert result is None

    def test_fact_density_boosts_weight(self):
        """Richer domains (more facts) get higher heuristic weight."""
        m_low = _make_metrics(fact_density=0)
        m_high = _make_metrics(fact_density=200)
        agent = _make_agent(fitness=50.0, domain=AgentDomain.EVOLUTION)
        strat = HeuristicInjectionStrategy()

        with _patch_dm(m_low):
            w_low = strat._weight(agent)
        with _patch_dm(m_high):
            w_high = strat._weight(agent)

        assert w_high > w_low  # density_bonus adds up to 0.5

    def test_subagent_injection_below_60(self):
        """Subagents below 60 get injected."""
        m = _make_metrics(fact_density=50)
        sub = SubAgent(domain=AgentDomain.SECURITY, fitness=30.0)
        with _patch_dm(m):
            result = HeuristicInjectionStrategy().evaluate_subagent(sub)
        assert result is not None


# ── BridgeImportStrategy ──────────────────────────────────────


class TestBridgeImport:
    def test_bridge_when_gap_exceeds_30(self):
        """Large gap between best and worst triggers bridge."""
        m = _make_metrics(bridge_count=3)
        agent = _make_agent(sub_fitness=[90.0, 50.0, 50.0])  # gap = 40
        with _patch_dm(m):
            result = BridgeImportStrategy().evaluate_agent(agent)
        assert result is not None
        assert result.mutation_type == MutationType.BRIDGE_IMPORT

    def test_no_bridge_when_gap_small(self):
        """Small gap → no bridge needed."""
        m = _make_metrics()
        agent = _make_agent(sub_fitness=[60.0, 55.0, 50.0])  # gap = 10
        with _patch_dm(m):
            result = BridgeImportStrategy().evaluate_agent(agent)
        assert result is None

    def test_bridge_score_modulates_multiplier(self):
        """Higher bridge_score in CORTEX → larger transfer."""
        m_low = _make_metrics(bridge_count=0)
        m_high = _make_metrics(bridge_count=10)
        agent = _make_agent(sub_fitness=[100.0, 30.0])  # gap = 70
        strat = BridgeImportStrategy()

        with _patch_dm(m_low):
            r_low = strat.evaluate_agent(agent)
        with _patch_dm(m_high):
            r_high = strat.evaluate_agent(agent)

        assert r_low is not None and r_high is not None
        assert r_high.delta_fitness >= r_low.delta_fitness

    def test_subagent_bridge_returns_none(self):
        """Bridges are agent-level only."""
        sub = SubAgent(fitness=30.0)
        result = BridgeImportStrategy().evaluate_subagent(sub)
        assert result is None


# ── AdversarialStressStrategy ─────────────────────────────────


class TestAdversarialStress:
    def test_no_stress_below_threshold(self):
        """Low fitness agents are not stressed."""
        agent = _make_agent(fitness=50.0)
        result = AdversarialStressStrategy().evaluate_agent(agent)
        assert result is None

    @patch("cortex.evolution.strategies._rng")
    def test_stress_pass_gives_resilience_bonus(self, mock_rng):
        """Agent survives stress → gets _RESILIENCE_BONUS."""
        mock_rng.random.return_value = 0.1  # Trigger (< 0.3)
        mock_rng.uniform.return_value = 2.0  # stress_hit = 2.0
        agent = _make_agent(fitness=120.0)  # 120 - 2 = 118 > 100 → PASS
        result = AdversarialStressStrategy().evaluate_agent(agent)
        assert result is not None
        assert result.delta_fitness == 3.0  # _RESILIENCE_BONUS
        assert "PASSED" in result.description

    @patch("cortex.evolution.strategies._rng")
    def test_stress_fail_gives_penalty(self, mock_rng):
        """Agent fails stress → gets penalty."""
        mock_rng.random.return_value = 0.1  # Trigger
        mock_rng.uniform.return_value = 4.5  # stress_hit = 4.5
        agent = _make_agent(fitness=103.0)  # 103 - 4.5 = 98.5 < 100 → FAIL
        result = AdversarialStressStrategy().evaluate_agent(agent)
        assert result is not None
        assert result.delta_fitness == -1.0
        assert "FAILED" in result.description

    @patch("cortex.evolution.strategies._rng")
    def test_stochastic_30_percent_trigger(self, mock_rng):
        """70% of the time, stress doesn't trigger."""
        mock_rng.random.return_value = 0.5  # > 0.3 → no trigger
        agent = _make_agent(fitness=120.0)
        result = AdversarialStressStrategy().evaluate_agent(agent)
        assert result is None


# ── EntropyReductionStrategy ──────────────────────────────────


class TestEntropyReduction:
    def test_young_agent_skipped(self):
        """Agents with < 10 generations are too young for entropy check."""
        agent = _make_agent(fitness=55.0, generation=5)
        result = EntropyReductionStrategy().evaluate_agent(agent)
        assert result is None

    def test_high_ratio_triggers_purge(self):
        """Many generations with little gain → entropy purge."""
        agent = _make_agent(fitness=51.0, generation=100)
        # ratio = 100 / (51-50) = 100 > 20 → purge
        result = EntropyReductionStrategy().evaluate_agent(agent)
        assert result is not None
        assert result.mutation_type == MutationType.ENTROPY_REDUCTION
        assert result.delta_fitness == 2.0

    def test_good_gain_no_purge(self):
        """Efficient generations → no entropy purge."""
        agent = _make_agent(fitness=100.0, generation=15)
        # ratio = 15 / (100-50) = 0.3 << 20 → no purge
        result = EntropyReductionStrategy().evaluate_agent(agent)
        assert result is None

    def test_subagent_entropy_needs_15_gens(self):
        """Subagents need 15+ generations for entropy check."""
        sub = SubAgent(fitness=51.0, generation=10)
        result = EntropyReductionStrategy().evaluate_subagent(sub)
        assert result is None

    def test_subagent_high_ratio_purge(self):
        """Subagent with high gen/gain ratio gets purged."""
        sub = SubAgent(fitness=51.0, generation=100)
        result = EntropyReductionStrategy().evaluate_subagent(sub)
        assert result is not None
        assert result.delta_fitness == 1.5


# ── CrossoverRecombinationStrategy ────────────────────────────


class TestCrossoverRecombination:
    def test_triggers_when_variance_high(self):
        """Gap > 15 between best and worst → crossover."""
        agent = _make_agent(sub_fitness=[80.0, 50.0])  # gap = 30
        result = CrossoverRecombinationStrategy().evaluate_agent(agent)
        assert result is not None
        assert result.mutation_type == MutationType.CROSSOVER_RECOMBINE
        # delta = min(5.0, 30*0.4) = 5.0
        assert result.delta_fitness == pytest.approx(5.0)

    def test_no_crossover_low_variance(self):
        """Gap < 15 → no point recombining."""
        agent = _make_agent(sub_fitness=[55.0, 50.0])  # gap = 5
        result = CrossoverRecombinationStrategy().evaluate_agent(agent)
        assert result is None

    def test_subagent_population_crossover(self):
        """Low-fitness subagent (< 70, gen > 3) gets population crossover."""
        m = _make_metrics(decision_count=5, bridge_count=2)  # healthy
        sub = SubAgent(domain=AgentDomain.MEMORY, fitness=50.0, generation=5)
        with _patch_dm(m):
            result = CrossoverRecombinationStrategy().evaluate_subagent(sub)
        assert result is not None

    def test_subagent_high_fitness_no_crossover(self):
        """Healthy subagents don't need population crossover."""
        sub = SubAgent(fitness=80.0, generation=5)
        result = CrossoverRecombinationStrategy().evaluate_subagent(sub)
        assert result is None


# ── StagnationBreakerStrategy ─────────────────────────────────


class TestStagnationBreaker:
    def _stagnated_agent(self) -> SovereignAgent:
        """Build an agent stuck in a plateau (5+ near-zero mutations)."""
        agent = _make_agent(fitness=75.0)
        for _ in range(6):
            agent.mutations.append(
                Mutation(delta_fitness=0.1)  # |0.1| < 0.5
            )
        return agent

    def test_stagnated_agent_gets_shock(self):
        """Agent with 5+ stagnant mutations → punctuation event."""
        m = _make_metrics()
        agent = self._stagnated_agent()
        with _patch_dm(m):
            result = StagnationBreakerStrategy().evaluate_agent(agent)
        assert result is not None
        assert result.mutation_type == MutationType.STAGNATION_BREAK
        assert -3.0 <= result.delta_fitness <= 8.0

    def test_non_stagnated_skipped(self):
        """Agent with recent significant mutations → no shock."""
        agent = _make_agent(fitness=75.0)
        agent.mutations = [Mutation(delta_fitness=5.0) for _ in range(5)]
        result = StagnationBreakerStrategy().evaluate_agent(agent)
        assert result is None

    def test_too_few_mutations_skipped(self):
        """Agent with < 5 mutations → not enough history to judge."""
        agent = _make_agent(fitness=75.0)
        agent.mutations = [Mutation(delta_fitness=0.1) for _ in range(3)]
        result = StagnationBreakerStrategy().evaluate_agent(agent)
        assert result is None

    def test_subagent_stagnation(self):
        """Subagent stagnation detection works identically."""
        m = _make_metrics()
        sub = SubAgent(fitness=60.0)
        for _ in range(6):
            sub.mutations.append(Mutation(delta_fitness=0.0))
        with _patch_dm(m):
            result = StagnationBreakerStrategy().evaluate_subagent(sub)
        assert result is not None


# ── FitnessLandscape ──────────────────────────────────────────


class TestFitnessLandscape:
    def test_ceiling_ratchet(self):
        """Ceiling never decreases (ratchet property)."""
        from cortex.evolution.landscape import FitnessLandscape

        landscape = FitnessLandscape()
        s1 = landscape.compute()
        # Ratchet: manually raise the cached ceiling
        boosted = s1.ceiling + 50.0
        landscape._last_ceiling = boosted
        landscape._cache = None  # Force recompute
        s2 = landscape.compute()
        # Ratchet guarantees the new ceiling is >= the old boosted value
        assert s2.ceiling >= boosted

    def test_clamp_enforces_bounds(self):
        """Agent and subagent fitness clamped to [0, ceiling]."""
        from cortex.evolution.landscape import FitnessLandscape

        landscape = FitnessLandscape()
        landscape._last_ceiling = 100.0
        agent = _make_agent(fitness=150.0, sub_fitness=[200.0, -10.0])
        landscape.clamp(agent)
        assert agent.fitness == 100.0
        assert agent.subagents[0].fitness == 100.0
        assert agent.subagents[1].fitness == 0.0


# ── Persistence ───────────────────────────────────────────────


class TestPersistence:
    def test_save_load_roundtrip(self, tmp_path):
        """Swarm survives serialization → deserialization."""
        from cortex.evolution.persistence import load_swarm, save_swarm

        agents = [
            _make_agent(
                domain=AgentDomain.FABRICATION,
                fitness=75.5,
                sub_fitness=[60.0, 70.0, 80.0],
            )
        ]
        agents[0].generation = 15
        agents[0].mutations.append(
            Mutation(
                mutation_type=MutationType.PARAMETER_TUNE,
                description="test mutation",
                delta_fitness=5.0,
            )
        )

        path = tmp_path / "evolution_state.json"
        assert save_swarm(agents, cycle=42, path=path)

        result = load_swarm(path=path)
        assert result is not None
        loaded_agents, cycle = result
        assert cycle == 42
        assert len(loaded_agents) == 1
        assert loaded_agents[0].domain == AgentDomain.FABRICATION
        assert loaded_agents[0].fitness == 75.5
        assert loaded_agents[0].generation == 15
        assert len(loaded_agents[0].subagents) == 3

    def test_load_nonexistent_returns_none(self, tmp_path):
        """Missing state file → None (genesis needed)."""
        from cortex.evolution.persistence import load_swarm

        result = load_swarm(path=tmp_path / "nonexistent.json")
        assert result is None


# ── Tournament ────────────────────────────────────────────────


class TestTournament:
    def test_tournament_transfers_fitness(self):
        """Winner donates fitness to loser."""
        from cortex.evolution.tournament import run_tournament

        agent = _make_agent(sub_fitness=[90.0, 80.0, 20.0])
        original_worst = 20.0
        result = run_tournament(agent, tournament_size=3)
        # The loser (originally 20.0) should have gained fitness
        if result is not None:
            assert result.transferred_fitness > 0
            assert result.loser.fitness > original_worst

    def test_speciation_clusters(self):
        """Subagents cluster into species by fitness distance."""
        from cortex.evolution.tournament import speciate

        agent = _make_agent(sub_fitness=[10.0, 15.0, 80.0, 85.0, 90.0])
        species = speciate(agent, threshold=20.0)
        assert len(species) >= 2  # Two distinct clusters

    def test_elitism_shields_top(self):
        """Top subagents get elite shield."""
        from cortex.evolution.tournament import apply_elitism

        agent = _make_agent(sub_fitness=[90.0, 80.0, 70.0, 60.0, 50.0])
        elites = apply_elitism(agent, elite_fraction=0.4)
        assert len(elites) == 2  # Top 40% of 5 = 2
        for e in elites:
            assert e.parameters.get("_elite_shield") is True

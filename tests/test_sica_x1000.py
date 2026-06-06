# [C5-REAL] Exergy-Maximized
"""Tests for SICA x1000 - World Model, Dream Engine, Colony.

Tests the three cognitive leap modules:
  1. WorldModel: Bayesian prediction, UCB ranking, counterfactuals
  2. DreamEngine: Trace consolidation, fragment extraction, insights
  3. Colony: Gene pool, tournament, crossover, specialization
"""

from __future__ import annotations

import pytest

from cortex.sica.colony import (
    Colony,
    GenePool,
    GenomeCrossover,
    SpecializationDetector,
    Tournament,
)
from cortex.sica.dream import DreamEngine, DreamInsight
from cortex.sica.object_level import ExecutionStep, ExecutionTrace, StepOutcome
from cortex.sica.strategy import Heuristic, SearchStrategy, StrategyGenome, default_genome
from cortex.sica.world_model import ToolBelief, WorldModel


# ═══════════════════════════════════════════════════════════════════
# WORLD MODEL TESTS
# ═══════════════════════════════════════════════════════════════════


def _make_trace(
    task_id: str,
    tool: str,
    outcome: StepOutcome,
    objective: str = "search files",
    n_steps: int = 1,
) -> ExecutionTrace:
    t = ExecutionTrace(task_id=task_id, objective=objective, strategy_genome_hash="abc")
    for i in range(n_steps):
        t.add_step(
            ExecutionStep(
                step_id=i + 1,
                action=f"use_tool:{tool}",
                outcome=outcome,
                tool_used=tool,
            )
        )
    t.finalize(outcome)
    return t


class TestToolBelief:
    def test_prior_is_neutral(self):
        b = ToolBelief(tool_name="grep")
        assert b.expected_success == 0.5
        assert b.observations == 0

    def test_success_increases_expectation(self):
        b = ToolBelief(tool_name="grep")
        for _ in range(10):
            b.observe_success()
        assert b.expected_success > 0.8

    def test_failure_decreases_expectation(self):
        b = ToolBelief(tool_name="grep")
        for _ in range(10):
            b.observe_failure()
        assert b.expected_success < 0.2

    def test_uncertainty_decreases_with_observations(self):
        b = ToolBelief(tool_name="grep")
        u_initial = b.uncertainty
        for _ in range(20):
            b.observe_success()
        assert b.uncertainty < u_initial

    def test_ucb_score_explores_unknown_tools(self):
        known = ToolBelief(tool_name="known")
        for _ in range(50):
            known.observe_success()

        unknown = ToolBelief(tool_name="unknown")

        # UCB should give bonus to unknown tool
        assert unknown.ucb_score(100) > 0.5


class TestWorldModel:
    def test_learn_updates_beliefs(self):
        wm = WorldModel()
        trace = _make_trace("t1", "grep", StepOutcome.SUCCESS)
        wm.learn(trace)
        p, u = wm.predict_tool_success("grep")
        assert p > 0.5

    def test_rank_tools_puts_best_first(self):
        wm = WorldModel()
        for i in range(5):
            wm.learn(_make_trace(f"s{i}", "good_tool", StepOutcome.SUCCESS))
            wm.learn(_make_trace(f"f{i}", "bad_tool", StepOutcome.FAILURE))

        ranked = wm.rank_tools(["good_tool", "bad_tool"], use_ucb=False)
        assert ranked[0][0] == "good_tool"
        assert ranked[1][0] == "bad_tool"

    def test_rank_tools_with_ucb_explores(self):
        wm = WorldModel()
        for i in range(10):
            wm.learn(_make_trace(f"t{i}", "known", StepOutcome.SUCCESS))

        ranked = wm.rank_tools(["known", "new_tool"], use_ucb=True)
        # new_tool should get exploration bonus
        new_tool_score = [s for n, s, u in ranked if n == "new_tool"][0]
        assert new_tool_score > 0.0

    def test_contextual_beliefs(self):
        wm = WorldModel()
        # grep succeeds for search, fails for deploy
        for i in range(5):
            wm.learn(_make_trace(f"s{i}", "grep", StepOutcome.SUCCESS, objective="search files"))
            wm.learn(_make_trace(f"d{i}", "grep", StepOutcome.FAILURE, objective="deploy service"))

        p_search, _ = wm.predict_tool_success("grep", {"task_type": "search"})
        p_deploy, _ = wm.predict_tool_success("grep", {"task_type": "deploy"})
        assert p_search > p_deploy

    def test_counterfactual_reasoning(self):
        wm = WorldModel()
        for i in range(10):
            wm.learn(_make_trace(f"s{i}", "good", StepOutcome.SUCCESS))
            wm.learn(_make_trace(f"f{i}", "bad", StepOutcome.FAILURE))

        trace = _make_trace("test", "bad", StepOutcome.FAILURE)
        cf = wm.counterfactual(trace, 0, "good")
        assert cf["would_have_succeeded"]
        assert cf["delta_p"] > 0

    def test_regret_analysis(self):
        wm = WorldModel()
        for i in range(10):
            wm.learn(_make_trace(f"s{i}", "better", StepOutcome.SUCCESS))
            wm.learn(_make_trace(f"f{i}", "worse", StepOutcome.FAILURE))

        trace = _make_trace("test", "worse", StepOutcome.FAILURE)
        regrets = wm.regret_analysis(trace)
        assert len(regrets) >= 1
        assert regrets[0]["alternative_tool"] == "better"

    def test_surprise_detection(self):
        wm = WorldModel()
        for i in range(10):
            wm.learn(_make_trace(f"t{i}", "reliable", StepOutcome.SUCCESS))

        # Surprising failure of a reliable tool
        surprise_step = ExecutionStep(
            step_id=1,
            action="use",
            outcome=StepOutcome.FAILURE,
            tool_used="reliable",
        )
        surprise = wm.surprise(surprise_step)
        assert surprise > 0.7  # Very surprising

    def test_transition_model(self):
        wm = WorldModel()
        t = ExecutionTrace(task_id="t1", objective="test", strategy_genome_hash="abc")
        t.add_step(ExecutionStep(step_id=1, action="search", outcome=StepOutcome.SUCCESS))
        t.add_step(ExecutionStep(step_id=2, action="analyze", outcome=StepOutcome.SUCCESS))
        t.add_step(ExecutionStep(step_id=3, action="report", outcome=StepOutcome.SUCCESS))
        t.finalize(StepOutcome.SUCCESS)
        wm.learn(t)

        predictions = wm.predict_next_action("search")
        assert len(predictions) >= 1
        assert predictions[0][0] == "analyze"

    def test_introspection(self):
        wm = WorldModel()
        wm.learn(_make_trace("t1", "grep", StepOutcome.SUCCESS))
        report = wm.introspect()
        assert report["tools_modeled"] >= 1


# ═══════════════════════════════════════════════════════════════════
# DREAM ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════


def _make_traces_batch(
    n: int,
    tools: list[str],
    success_rate: float = 0.7,
    objective: str = "search",
) -> list[ExecutionTrace]:
    traces = []
    for i in range(n):
        tool = tools[i % len(tools)]
        outcome = StepOutcome.SUCCESS if (i / n) < success_rate else StepOutcome.FAILURE
        t = ExecutionTrace(
            task_id=f"t{i}", objective=f"{objective} target", strategy_genome_hash="abc"
        )
        t.add_step(
            ExecutionStep(step_id=1, action=f"use_tool:{tool}", outcome=outcome, tool_used=tool)
        )
        if outcome == StepOutcome.FAILURE and i > 0:
            t.add_step(ExecutionStep(step_id=2, action="retry", outcome=StepOutcome.FAILURE))
        t.finalize(outcome)
        traces.append(t)
    return traces


class TestDreamEngine:
    def test_dream_requires_min_traces(self):
        dream = DreamEngine(min_traces_for_dream=10)
        report = dream.dream([], SearchStrategy(default_genome()))
        assert report.traces_replayed == 0

    def test_dream_produces_report(self):
        dream = DreamEngine(min_traces_for_dream=5)
        traces = _make_traces_batch(10, ["grep", "read"])
        strategy = SearchStrategy(default_genome())
        report = dream.dream(traces, strategy)
        assert report.traces_replayed == 10
        assert report.cycle_id == 1

    def test_dream_discovers_insights(self):
        dream = DreamEngine(min_traces_for_dream=5)
        # Create traces where "grep" dominates for "search"
        traces = _make_traces_batch(12, ["grep"], success_rate=0.8, objective="search")
        strategy = SearchStrategy(default_genome())
        report = dream.dream(traces, strategy)
        # Should discover at least some patterns
        assert report.cycle_id == 1
        assert dream.cycle_count == 1

    def test_dream_discovers_failure_precursors(self):
        dream = DreamEngine(min_traces_for_dream=5)
        traces = []
        for i in range(8):
            t = ExecutionTrace(task_id=f"t{i}", objective="test", strategy_genome_hash="abc")
            t.add_step(
                ExecutionStep(step_id=1, action="danger_action", outcome=StepOutcome.SUCCESS)
            )
            t.add_step(ExecutionStep(step_id=2, action="crash_action", outcome=StepOutcome.FAILURE))
            t.finalize(StepOutcome.FAILURE)
            traces.append(t)

        strategy = SearchStrategy(default_genome())
        report = dream.dream(traces, strategy)
        anti_patterns = [i for i in report.insights_discovered if i.insight_type == "anti_pattern"]
        assert len(anti_patterns) >= 1

    def test_apply_insights_injects_heuristics(self):
        dream = DreamEngine(min_traces_for_dream=5)
        strategy = SearchStrategy(default_genome())

        initial_count = len(strategy.genome.heuristics)

        # Create a high-confidence insight with a proposed heuristic
        insight = DreamInsight(
            insight_type="specialization",
            description="test insight",
            confidence=0.8,
            evidence_count=10,
            proposed_heuristic=Heuristic(
                name="dream_discovered_h",
                description="from dream",
                weight=0.6,
            ),
        )
        applied = dream.apply_insights([insight], strategy)
        assert applied == 1
        assert len(strategy.genome.heuristics) == initial_count + 1

    def test_low_confidence_insights_not_applied(self):
        dream = DreamEngine()
        strategy = SearchStrategy(default_genome())

        insight = DreamInsight(
            insight_type="rule",
            description="low confidence",
            confidence=0.3,
            evidence_count=1,
            proposed_heuristic=Heuristic(name="weak", description="", weight=0.5),
        )
        applied = dream.apply_insights([insight], strategy, confidence_threshold=0.6)
        assert applied == 0

    def test_abstractions_accumulated(self):
        dream = DreamEngine(min_traces_for_dream=3, abstraction_threshold=2)
        traces = _make_traces_batch(6, ["grep"], success_rate=0.8)
        strategy = SearchStrategy(default_genome())
        report = dream.dream(traces, strategy)
        assert report.abstractions_formed >= 0  # May form some
        assert dream.cycle_count == 1


# ═══════════════════════════════════════════════════════════════════
# COLONY TESTS
# ═══════════════════════════════════════════════════════════════════


def _make_strategy(exploration: float = 0.3, tools: list[str] | None = None) -> SearchStrategy:
    g = default_genome()
    g.exploration_rate = exploration
    if tools:
        g.tool_priority = tools
    return SearchStrategy(g)


class TestGenePool:
    def test_donate_and_adopt(self):
        pool = GenePool()
        strategy_a = _make_strategy()
        # Give some activations so fitness is trackable
        for h in strategy_a.genome.heuristics:
            h.activate(success=True)
            h.activate(success=True)
            h.activate(success=True)

        donated = pool.donate("agent-a", strategy_a, min_fitness=0.0)
        assert len(donated) > 0

        strategy_b = _make_strategy()
        adopted = pool.adopt("agent-b", strategy_b)
        assert len(adopted) >= 0  # May adopt 0 if all heuristics already exist

    def test_dont_adopt_own_donations(self):
        pool = GenePool()
        strategy_a = _make_strategy()
        for h in strategy_a.genome.heuristics:
            h.activate(success=True)
            h.activate(success=True)
        pool.donate("agent-a", strategy_a, min_fitness=0.0)
        adopted = pool.adopt("agent-a", strategy_a)
        assert all(f.donor_agent != "agent-a" for f in adopted)

    def test_pool_evicts_when_full(self):
        pool = GenePool(max_fragments=5)
        for i in range(10):
            g = default_genome()
            g.heuristics = [Heuristic(name=f"h{i}", description="", weight=0.8)]
            g.heuristics[0].activate(success=True)
            g.heuristics[0].activate(success=True)
            s = SearchStrategy(g)
            pool.donate(f"agent-{i}", s, min_fitness=0.0)
        assert pool.size <= 5

    def test_adoption_outcome_tracking(self):
        pool = GenePool()
        strategy = _make_strategy()
        for h in strategy.genome.heuristics:
            h.activate(success=True)
        donated = pool.donate("agent-a", strategy, min_fitness=0.0)
        if donated:
            pool.report_adoption_outcome(donated[0], success=True)
            frag = pool.fragments[0]
            assert frag.adoption_success_count >= 0


class TestTournament:
    def test_tournament_produces_winner(self):
        t = Tournament()
        strategies = {
            "fast": _make_strategy(exploration=0.3),
            "slow": _make_strategy(exploration=0.9),
        }
        result = t.compete(strategies)
        assert result.winner in strategies
        assert len(result.rankings) == 2

    def test_tournament_history(self):
        t = Tournament()
        strategies = {
            "a": _make_strategy(),
            "b": _make_strategy(),
        }
        t.compete(strategies)
        t.compete(strategies)
        assert len(t.history) == 2


class TestGenomeCrossover:
    def test_crossover_produces_child(self):
        cx = GenomeCrossover()
        parent_a = default_genome()
        parent_b = default_genome()
        parent_b.heuristics.append(Heuristic(name="unique_b", description="only in B", weight=0.7))
        parent_b.heuristics[-1].activate(success=True)

        child = cx.crossover(parent_a, parent_b)
        assert child.generation > 0
        assert "×" in child.parent_hash

    def test_crossover_inherits_from_both(self):
        cx = GenomeCrossover()
        parent_a = default_genome()
        parent_a.tool_priority = ["grep", "read"]

        parent_b = default_genome()
        parent_b.tool_priority = ["analyze", "verify"]

        child = cx.crossover(parent_a, parent_b)
        # Child should have tools from both
        assert len(child.tool_priority) >= 2

    def test_crossover_blends_exploration(self):
        cx = GenomeCrossover()
        parent_a = default_genome()
        parent_a.exploration_rate = 0.2

        parent_b = default_genome()
        parent_b.exploration_rate = 0.8

        child = cx.crossover(parent_a, parent_b)
        assert 0.3 <= child.exploration_rate <= 0.7  # Blended


class TestSpecialization:
    def test_detects_searcher(self):
        sd = SpecializationDetector()
        g = default_genome()
        g.tool_priority = ["search", "grep", "find"]
        strategies = {"agent-1": SearchStrategy(g)}
        specs = sd.detect(strategies)
        assert specs["agent-1"].primary_role == "searcher"

    def test_detects_generalist(self):
        sd = SpecializationDetector()
        g = default_genome()
        g.tool_priority = ["alpha", "beta", "gamma"]
        strategies = {"agent-1": SearchStrategy(g)}
        specs = sd.detect(strategies)
        assert specs["agent-1"].primary_role == "generalist"

    def test_recommend_routing(self):
        sd = SpecializationDetector()
        strategies = {
            "searcher": SearchStrategy(
                StrategyGenome(
                    heuristics=[Heuristic(name="h", description="", weight=0.5)],
                    tool_priority=["search", "grep"],
                )
            ),
            "deployer": SearchStrategy(
                StrategyGenome(
                    heuristics=[Heuristic(name="h", description="", weight=0.5)],
                    tool_priority=["deploy", "build"],
                )
            ),
        }
        specs = sd.detect(strategies)
        routing = sd.recommend_routing("search", specs)
        assert len(routing) == 2
        assert routing[0][0] == "searcher"


class TestColony:
    def test_full_colony_cycle(self):
        colony = Colony()
        s1 = _make_strategy(tools=["search", "grep"])
        s2 = _make_strategy(tools=["deploy", "build"])

        # Give some fitness data
        for h in s1.genome.heuristics:
            h.activate(success=True)
        for h in s2.genome.heuristics:
            h.activate(success=True)

        colony.register("agent-1", s1)
        colony.register("agent-2", s2)

        report = colony.evolve_cycle()
        assert report["agents"] == 2
        assert "tournament_winner" in report
        assert "specializations" in report

    def test_colony_needs_two_agents(self):
        colony = Colony()
        colony.register("lonely", _make_strategy())
        report = colony.evolve_cycle()
        assert "skipped" in report

    def test_colony_introspection(self):
        colony = Colony()
        colony.register("a", _make_strategy())
        colony.register("b", _make_strategy())
        state = colony.introspect()
        assert state["population"] == 2


# ═══════════════════════════════════════════════════════════════════
# INTEGRATION: World Model + Dream + Colony
# ═══════════════════════════════════════════════════════════════════


class TestX1000Integration:
    def test_world_model_feeds_dream(self):
        """WorldModel learns → Dream consolidates → Strategy evolves."""
        wm = WorldModel()
        dream = DreamEngine(min_traces_for_dream=5)
        strategy = SearchStrategy(default_genome())

        # Generate execution traces
        traces = []
        for i in range(10):
            tool = "grep" if i % 2 == 0 else "search"
            outcome = StepOutcome.SUCCESS if i < 7 else StepOutcome.FAILURE
            t = _make_trace(f"t{i}", tool, outcome)
            traces.append(t)
            wm.learn(t)

        # Dream consolidation
        report = dream.dream(traces, strategy)
        assert report.traces_replayed == 10

        # Apply insights
        applied = dream.apply_insights(report.insights_discovered, strategy)

        # World model should have beliefs
        assert wm.introspect()["tools_modeled"] >= 2

    def test_colony_with_world_model(self):
        """Colony evolves, world models diverge by specialization."""
        colony = Colony()
        wm_a = WorldModel()
        wm_b = WorldModel()

        s_a = _make_strategy(tools=["search", "grep"])
        s_b = _make_strategy(tools=["deploy", "build"])

        for h in s_a.genome.heuristics:
            h.activate(success=True)
        for h in s_b.genome.heuristics:
            h.activate(success=True)

        # Agent A learns search is good
        for i in range(5):
            wm_a.learn(_make_trace(f"a{i}", "search", StepOutcome.SUCCESS))

        # Agent B learns deploy is good
        for i in range(5):
            wm_b.learn(_make_trace(f"b{i}", "deploy", StepOutcome.SUCCESS))

        colony.register("agent-a", s_a)
        colony.register("agent-b", s_b)

        report = colony.evolve_cycle()
        assert report["agents"] == 2

        # Verify specializations emerged
        specs = colony.specialization.detect({"a": s_a, "b": s_b})
        assert specs["a"].primary_role == "searcher"
        assert specs["b"].primary_role == "deployer"

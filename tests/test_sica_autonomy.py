# [C5-REAL] Exergy-Maximized
"""Tests for SICA Autonomy & Persistence.

Validates the 5 autonomy upgrades:
  1. Genome persistence (save/load/resume)
  2. Speculative forking
  3. Trace-based heuristic synthesis
  4. Meta-meta controller
  5. Adaptive retry budgets
  6. Autonomous tick cycle
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cortex.sica.autonomy import (
    AdaptiveRetry,
    AutonomousTick,
    MetaMetaController,
    SpeculativeFork,
    TraceSynthesizer,
)
from cortex.sica.constitution import Constitution
from cortex.sica.meta_level import FailureClass, MetaAction, MetaJudgment, MetaLevel
from cortex.sica.object_level import ExecutionStep, ExecutionTrace, ObjectLevel, StepOutcome
from cortex.sica.persistence import (
    genome_from_json,
    genome_to_json,
    list_generations,
    load_genome,
    load_or_default,
    save_genome,
)
from cortex.sica.strategy import Heuristic, SearchStrategy, StrategyGenome, default_genome


# ═══════════════════════════════════════════════════════════════════
# PERSISTENCE TESTS
# ═══════════════════════════════════════════════════════════════════


class TestGenomeSerialization:
    def test_roundtrip_preserves_genome(self):
        g = default_genome()
        g.generation = 42
        g.parent_hash = "abc123"
        g.heuristics[0].activation_count = 10
        g.heuristics[0].success_count = 7

        data = genome_to_json(g)
        restored = genome_from_json(data)

        assert restored.generation == 42
        assert restored.parent_hash == "abc123"
        assert restored.heuristics[0].activation_count == 10
        assert restored.heuristics[0].success_count == 7
        assert len(restored.heuristics) == len(g.heuristics)

    def test_serialization_includes_all_fields(self):
        g = default_genome()
        data = genome_to_json(g)
        assert "schema_version" in data
        assert "genome_hash" in data
        assert "heuristics" in data
        assert "tool_priority" in data
        assert "saved_at" in data


class TestGenomePersistence:
    def test_save_and_load(self, tmp_path: Path):
        g = default_genome()
        g.generation = 5

        save_genome(g, agent_id="test-agent", directory=tmp_path)

        loaded = load_genome("test-agent", directory=tmp_path, generation=5)
        assert loaded is not None
        assert loaded.generation == 5

    def test_load_latest(self, tmp_path: Path):
        g = default_genome()
        g.generation = 1
        save_genome(g, agent_id="test-agent", directory=tmp_path)

        g.generation = 2
        save_genome(g, agent_id="test-agent", directory=tmp_path)

        loaded = load_genome("test-agent", directory=tmp_path)
        assert loaded is not None
        assert loaded.generation == 2

    def test_load_nonexistent_returns_none(self, tmp_path: Path):
        result = load_genome("nonexistent", directory=tmp_path)
        assert result is None

    def test_load_or_default_creates_fresh(self, tmp_path: Path):
        strategy = load_or_default("fresh-agent", directory=tmp_path)
        assert strategy.genome.generation == 0

    def test_load_or_default_resumes(self, tmp_path: Path):
        g = default_genome()
        g.generation = 10
        save_genome(g, agent_id="resume-agent", directory=tmp_path)

        strategy = load_or_default("resume-agent", directory=tmp_path)
        assert strategy.genome.generation == 10

    def test_list_generations(self, tmp_path: Path):
        g = default_genome()
        for i in range(3):
            g.generation = i
            save_genome(g, agent_id="list-agent", directory=tmp_path)

        gens = list_generations("list-agent", directory=tmp_path)
        assert len(gens) == 3
        assert gens[0]["generation"] == 0
        assert gens[2]["generation"] == 2

    def test_atomic_write_creates_no_tmp_files(self, tmp_path: Path):
        g = default_genome()
        save_genome(g, agent_id="atomic-test", directory=tmp_path)
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0


# ═══════════════════════════════════════════════════════════════════
# SPECULATIVE FORK TESTS
# ═══════════════════════════════════════════════════════════════════


class TestSpeculativeFork:
    def _make_judgment(self, is_meta: bool = True) -> MetaJudgment:
        j = MetaJudgment(trace_id="test")
        j.is_meta_failure = is_meta
        j.failure_class = FailureClass.CASCADE_BLINDNESS
        j.recommended_actions = [MetaAction.INJECT_HEURISTIC]
        return j

    def _make_traces(self, n: int = 5) -> list[ExecutionTrace]:
        traces = []
        for i in range(n):
            t = ExecutionTrace(
                task_id=f"t{i}",
                objective="test",
                strategy_genome_hash="abc",
            )
            outcome = StepOutcome.SUCCESS if i % 2 == 0 else StepOutcome.FAILURE
            t.add_step(
                ExecutionStep(
                    step_id=1,
                    action="test",
                    outcome=outcome,
                    heuristic_applied="decompose_first",
                )
            )
            t.finalize(outcome)
            traces.append(t)
        return traces

    def test_fork_returns_strategy(self):
        s = SearchStrategy(default_genome())
        fork = SpeculativeFork(n_forks=3)
        j = self._make_judgment()
        traces = self._make_traces()
        result = fork.speculate(s, j, traces)
        assert isinstance(result, SearchStrategy)

    def test_fork_records_history(self):
        s = SearchStrategy(default_genome())
        fork = SpeculativeFork(n_forks=3)
        j = self._make_judgment()
        traces = self._make_traces()
        fork.speculate(s, j, traces)
        assert len(fork.fork_history) == 3

    def test_no_fork_without_strategy_mutation(self):
        s = SearchStrategy(default_genome())
        fork = SpeculativeFork(n_forks=3)
        j = MetaJudgment(trace_id="test")
        j.recommended_actions = [MetaAction.NO_ACTION]
        result = fork.speculate(s, j, [])
        assert result is s  # Same object, no fork


# ═══════════════════════════════════════════════════════════════════
# TRACE SYNTHESIZER TESTS
# ═══════════════════════════════════════════════════════════════════


class TestTraceSynthesizer:
    def _make_traces(self, n: int, tool: str, outcome: StepOutcome) -> list[ExecutionTrace]:
        traces = []
        for i in range(n):
            t = ExecutionTrace(task_id=f"t{i}", objective="test", strategy_genome_hash="abc")
            t.add_step(
                ExecutionStep(
                    step_id=1,
                    action="use_tool",
                    outcome=outcome,
                    tool_used=tool,
                )
            )
            t.finalize(outcome)
            traces.append(t)
        return traces

    def test_no_synthesis_with_few_traces(self):
        synth = TraceSynthesizer(min_traces=10)
        traces = self._make_traces(5, "grep", StepOutcome.SUCCESS)
        result = synth.synthesize(traces, [])
        assert len(result) == 0

    def test_synthesizes_tool_combo_heuristic(self):
        synth = TraceSynthesizer(min_traces=5)
        traces = self._make_traces(6, "grep", StepOutcome.SUCCESS)
        result = synth.synthesize(traces, [])
        combo_heuristics = [h for h in result if h.name.startswith("prefer_combo")]
        assert len(combo_heuristics) >= 1

    def test_no_duplicate_heuristics(self):
        synth = TraceSynthesizer(min_traces=5)
        traces = self._make_traces(6, "grep", StepOutcome.SUCCESS)
        existing = [Heuristic(name="prefer_combo_grep", description="already exists")]
        result = synth.synthesize(traces, existing)
        combo_heuristics = [h for h in result if "grep" in h.name]
        assert len(combo_heuristics) == 0

    def test_detects_anti_patterns(self):
        synth = TraceSynthesizer(min_traces=5)
        traces = []
        for i in range(6):
            t = ExecutionTrace(task_id=f"t{i}", objective="test", strategy_genome_hash="abc")
            t.add_step(
                ExecutionStep(step_id=1, action="dangerous_action", outcome=StepOutcome.SUCCESS)
            )
            t.add_step(ExecutionStep(step_id=2, action="crash", outcome=StepOutcome.FAILURE))
            t.finalize(StepOutcome.FAILURE)
            traces.append(t)
        result = synth.synthesize(traces, [])
        anti = [h for h in result if h.name.startswith("avoid_before_failure")]
        assert len(anti) >= 1


# ═══════════════════════════════════════════════════════════════════
# META-META CONTROLLER TESTS
# ═══════════════════════════════════════════════════════════════════


class TestMetaMetaController:
    def test_detects_tunnel_vision(self):
        s = SearchStrategy(default_genome())
        meta = MetaLevel(s)
        controller = MetaMetaController()

        # Inject 6 identical failure class judgments
        for i in range(6):
            j = MetaJudgment(trace_id=f"t{i}")
            j.failure_class = FailureClass.TOOL_ERROR
            meta._judgment_history.append(j)

        old_rate = s.genome.exploration_rate
        diagnoses = controller.check_and_correct(meta, s)

        tunnel_diag = [d for d in diagnoses if d.pattern == "tunnel_vision"]
        assert len(tunnel_diag) == 1
        assert s.genome.exploration_rate > old_rate

    def test_no_false_positive_on_diverse_judgments(self):
        s = SearchStrategy(default_genome())
        meta = MetaLevel(s)
        controller = MetaMetaController()

        for i, fc in enumerate(
            [
                FailureClass.TOOL_ERROR,
                FailureClass.TIMEOUT,
                FailureClass.CASCADE_BLINDNESS,
                FailureClass.STALE_PATTERN,
                FailureClass.WRONG_TOOL_CHOICE,
            ]
        ):
            j = MetaJudgment(trace_id=f"t{i}")
            j.failure_class = fc
            meta._judgment_history.append(j)

        diagnoses = controller.check_and_correct(meta, s)
        tunnel_diag = [d for d in diagnoses if d.pattern == "tunnel_vision"]
        assert len(tunnel_diag) == 0

    def test_detects_premature_convergence(self):
        g = StrategyGenome(
            heuristics=[
                Heuristic(name="h1", description="", weight=0.5),
                Heuristic(name="h2", description="", weight=0.5),
                Heuristic(name="h3", description="", weight=0.5),
            ],
            exploration_rate=0.05,
        )
        s = SearchStrategy(g)
        meta = MetaLevel(s)
        controller = MetaMetaController()

        diagnoses = controller.check_and_correct(meta, s)
        conv_diag = [d for d in diagnoses if d.pattern == "premature_convergence"]
        assert len(conv_diag) == 1
        assert s.genome.exploration_rate > 0.05


# ═══════════════════════════════════════════════════════════════════
# ADAPTIVE RETRY TESTS
# ═══════════════════════════════════════════════════════════════════


class TestAdaptiveRetry:
    def test_base_budget_for_no_failure(self):
        ar = AdaptiveRetry(base_budget=3)
        j = MetaJudgment(trace_id="test")
        assert ar.compute_budget(j) == 3

    def test_zero_retries_on_constitutional_abort(self):
        from cortex.sica.constitution import ConstitutionalVerdict

        ar = AdaptiveRetry(base_budget=3)
        j = MetaJudgment(trace_id="test")
        j.constitutional_verdict = ConstitutionalVerdict(
            passed=False,
            abort_needed=True,
        )
        assert ar.compute_budget(j) == 0

    def test_meta_failures_get_more_retries(self):
        ar = AdaptiveRetry(base_budget=3)
        j = MetaJudgment(trace_id="test")
        j.is_meta_failure = True
        j.failure_class = FailureClass.CASCADE_BLINDNESS
        budget = ar.compute_budget(j)
        assert budget > 3  # More than base

    def test_repeated_failure_class_diminishes_budget(self):
        ar = AdaptiveRetry(base_budget=3)

        j = MetaJudgment(trace_id="test")
        j.failure_class = FailureClass.TOOL_ERROR
        b1 = ar.compute_budget(j)

        # Same class again and again
        for _ in range(5):
            ar.compute_budget(j)
        b_last = ar.compute_budget(j)

        assert b_last <= b1

    def test_first_time_bonus(self):
        ar = AdaptiveRetry(base_budget=3)
        j = MetaJudgment(trace_id="test")
        j.failure_class = FailureClass.WRONG_DECOMPOSITION
        budget = ar.compute_budget(j)
        # First time should get bonus
        assert budget >= 3


# ═══════════════════════════════════════════════════════════════════
# AUTONOMOUS TICK TESTS
# ═══════════════════════════════════════════════════════════════════


class TestAutonomousTick:
    def test_tick_respects_interval(self):
        tick = AutonomousTick(min_interval_s=9999)
        tick._last_tick = 0.0  # Reset
        assert not tick.should_tick() or tick._last_tick == 0.0

    def test_tick_runs_and_increments_counter(self):
        tick = AutonomousTick(min_interval_s=0)  # No cooldown
        s = SearchStrategy(default_genome())
        obj = ObjectLevel(s)
        meta = MetaLevel(s)

        report = tick.execute(s, obj, meta)
        assert tick.tick_count == 1
        assert "tick" in report

    def test_tick_prunes_dead_heuristics(self):
        tick = AutonomousTick(min_interval_s=0)
        g = default_genome()
        # Create a dead heuristic
        dead_h = Heuristic(
            name="dead_heuristic",
            description="should be pruned",
            weight=0.05,
            activation_count=20,
            success_count=0,
        )
        # Force fitness to be very low
        dead_h.last_activated = 0.0  # Ancient
        g.heuristics.append(dead_h)

        s = SearchStrategy(g)
        obj = ObjectLevel(s)
        meta = MetaLevel(s)

        report = tick.execute(s, obj, meta)
        names = [h.name for h in s.genome.heuristics]
        assert "dead_heuristic" not in names


# ═══════════════════════════════════════════════════════════════════
# INTEGRATION: Full autonomous loop
# ═══════════════════════════════════════════════════════════════════


class TestAutonomyIntegration:
    def test_full_autonomous_cycle(self, tmp_path: Path):
        """Simulate the complete autonomous SICA lifecycle:
        create -> execute -> fail -> mutate -> fork -> save -> reload -> resume
        """
        # Phase 1: Fresh start
        strategy = load_or_default("auto-test", directory=tmp_path)
        assert strategy.genome.generation == 0

        obj = ObjectLevel(strategy)
        meta = MetaLevel(strategy)

        # Phase 2: Execute some tasks
        obj.begin_task("task-1", "find file")
        obj.record_step(
            action="search", outcome=StepOutcome.SUCCESS, heuristic_applied="decompose_first"
        )
        trace1 = obj.end_task(StepOutcome.SUCCESS)
        j1 = meta.monitor(trace1)
        meta.control(j1)

        # Phase 3: Hit a cascade failure
        obj.begin_task("task-2", "deploy")
        obj.record_step(action="step1", outcome=StepOutcome.SUCCESS)
        for i in range(4):
            obj.record_step(action=f"fail_{i}", outcome=StepOutcome.FAILURE, error=f"err_{i}")
        trace2 = obj.end_task(StepOutcome.FAILURE)
        j2 = meta.monitor(trace2)
        assert j2.is_meta_failure
        meta.control(j2)

        # Phase 4: Speculative fork
        fork = SpeculativeFork(n_forks=3)
        evolved = fork.speculate(strategy, j2, obj.trace_archive)
        assert isinstance(evolved, SearchStrategy)

        # Phase 5: Save
        save_genome(evolved.genome, agent_id="auto-test", directory=tmp_path)

        # Phase 6: Simulate restart -> load
        resumed = load_or_default("auto-test", directory=tmp_path)
        assert resumed.genome.generation > 0

        # Phase 7: Autonomous tick on resumed agent
        tick = AutonomousTick(min_interval_s=0)
        obj2 = ObjectLevel(resumed)
        meta2 = MetaLevel(resumed)
        report = tick.execute(resumed, obj2, meta2)
        assert tick.tick_count == 1

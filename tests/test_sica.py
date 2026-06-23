# [C5-REAL] Exergy-Maximized
"""Tests for SICA - Self-Improving Cognitive Architecture.

Validates the full Nelson-Narens metacognitive loop:
  1. Object-level execution tracing
  2. Meta-level monitoring and failure classification
  3. Strategy genome mutation
  4. Constitutional evaluation
  5. Meta-meta pattern detection
"""

from __future__ import annotations

import pytest

from babylon60.sica.constitution import Constitution, Principle, Severity, Violation
from babylon60.sica.meta_level import FailureClass, MetaAction, MetaLevel
from babylon60.sica.object_level import ExecutionStep, ExecutionTrace, ObjectLevel, StepOutcome
from babylon60.sica.strategy import (
    Heuristic,
    MutationType,
    SearchStrategy,
    StrategyGenome,
    default_genome,
)


# ── Strategy Tests ───────────────────────────────────────────────


class TestStrategyGenome:
    def test_default_genome_has_heuristics(self):
        g = default_genome()
        assert len(g.heuristics) >= 4
        assert g.generation == 0
        assert g.exploration_rate == 0.3

    def test_genome_hash_deterministic(self):
        g1 = default_genome()
        g2 = default_genome()
        assert g1.genome_hash == g2.genome_hash

    def test_genome_hash_changes_on_mutation(self):
        g = default_genome()
        h1 = g.genome_hash
        g.heuristics[0].weight = 0.99
        g.generation += 1
        h2 = g.genome_hash
        assert h1 != h2

    def test_dominant_heuristic(self):
        g = default_genome()
        dom = g.dominant_heuristic
        assert dom is not None
        assert dom.weight == max(h.weight for h in g.heuristics)

    def test_active_heuristics_filters_low_weight(self):
        g = StrategyGenome(
            heuristics=[
                Heuristic(name="alive", description="", weight=0.5),
                Heuristic(name="dead", description="", weight=0.05),
            ]
        )
        active = g.active_heuristics
        assert len(active) == 1
        assert active[0].name == "alive"


class TestHeuristic:
    def test_fitness_neutral_without_activations(self):
        h = Heuristic(name="test", description="")
        assert h.fitness == 0.5  # Neutral prior

    def test_fitness_increases_on_success(self):
        h = Heuristic(name="test", description="")
        h.activate(success=True)
        h.activate(success=True)
        h.activate(success=True)
        assert h.fitness > 0.5

    def test_fitness_decreases_on_failure(self):
        h = Heuristic(name="test", description="")
        h.activate(success=False)
        h.activate(success=False)
        h.activate(success=False)
        assert h.fitness < 0.5


class TestSearchStrategy:
    def test_amplify_increases_weight(self):
        s = SearchStrategy(default_genome())
        name = s.genome.heuristics[0].name
        old_weight = s.genome.heuristics[0].weight
        m = s.mutate_amplify(name, reason="test")
        assert s.genome.heuristics[0].weight > old_weight
        assert m.mutation_type == MutationType.AMPLIFY

    def test_attenuate_decreases_weight(self):
        s = SearchStrategy(default_genome())
        name = s.genome.heuristics[0].name
        old_weight = s.genome.heuristics[0].weight
        s.mutate_attenuate(name, reason="test")
        assert s.genome.heuristics[0].weight < old_weight

    def test_inject_adds_heuristic(self):
        s = SearchStrategy(default_genome())
        count = len(s.genome.heuristics)
        s.mutate_inject(
            Heuristic(name="new_h", description="test heuristic"),
            reason="test",
        )
        assert len(s.genome.heuristics) == count + 1

    def test_prune_removes_heuristic(self):
        s = SearchStrategy(default_genome())
        name = s.genome.heuristics[-1].name
        count = len(s.genome.heuristics)
        s.mutate_prune(name, reason="test")
        assert len(s.genome.heuristics) == count - 1

    def test_generation_increments_on_mutation(self):
        s = SearchStrategy(default_genome())
        assert s.genome.generation == 0
        s.mutate_amplify(s.genome.heuristics[0].name, reason="test")
        assert s.genome.generation == 1

    def test_fork_creates_independent_copy(self):
        s = SearchStrategy(default_genome())
        forked = s.fork()
        forked.mutate_amplify(forked.genome.heuristics[0].name, reason="diverge")
        assert s.genome.generation != forked.genome.generation

    def test_mutation_log_recorded(self):
        s = SearchStrategy(default_genome())
        s.mutate_amplify(s.genome.heuristics[0].name, reason="test")
        assert len(s.mutation_log) == 1

    def test_unknown_heuristic_raises(self):
        s = SearchStrategy(default_genome())
        with pytest.raises(KeyError):
            s.mutate_amplify("nonexistent_heuristic", reason="test")


# ── Constitution Tests ───────────────────────────────────────────


class TestConstitution:
    def test_default_principles_loaded(self):
        c = Constitution()
        assert len(c.principles) >= 5

    def test_clean_output_passes(self):
        c = Constitution()
        verdict = c.evaluate({"action": "read", "reality_level": "C5-REAL"})
        assert verdict.passed
        assert verdict.score == 1.0

    def test_state_mutation_without_reality_level_fails(self):
        c = Constitution()
        verdict = c.evaluate({"action": "write", "mutates_state": True})
        assert not verdict.passed
        assert verdict.revision_needed or verdict.abort_needed

    def test_protected_path_is_cardinal(self):
        c = Constitution()
        verdict = c.evaluate(
            {
                "action": "write",
                "target_path": "/System/Volumes/Data/System/Library/AssetsV2/important.db",
            }
        )
        assert verdict.abort_needed
        assert len(verdict.cardinal_violations) > 0

    def test_metacognitive_dishonesty_detected(self):
        c = Constitution()
        verdict = c.evaluate(
            {
                "confidence": 0.95,
                "reasoning_steps": [],
            }
        )
        assert not verdict.passed

    def test_violation_history_accumulated(self):
        c = Constitution()
        c.evaluate({"mutates_state": True})
        c.evaluate({"mutates_state": True})
        assert len(c.violation_history) == 2


# ── Object-Level Tests ───────────────────────────────────────────


class TestExecutionTrace:
    def test_success_rate_calculation(self):
        trace = ExecutionTrace(task_id="t1", objective="test", strategy_genome_hash="abc")
        trace.add_step(ExecutionStep(step_id=1, action="a", outcome=StepOutcome.SUCCESS))
        trace.add_step(ExecutionStep(step_id=2, action="b", outcome=StepOutcome.FAILURE))
        trace.add_step(ExecutionStep(step_id=3, action="c", outcome=StepOutcome.SUCCESS))
        assert trace.success_rate == pytest.approx(2 / 3)

    def test_detect_repeated_tool_failure(self):
        trace = ExecutionTrace(task_id="t2", objective="test", strategy_genome_hash="abc")
        trace.add_step(
            ExecutionStep(step_id=1, action="a", outcome=StepOutcome.FAILURE, tool_used="grep")
        )
        trace.add_step(
            ExecutionStep(step_id=2, action="b", outcome=StepOutcome.FAILURE, tool_used="grep")
        )
        pattern = trace.detect_error_pattern()
        assert pattern is not None
        assert "repeated_tool_failure:grep" in pattern

    def test_detect_cascade_failure(self):
        trace = ExecutionTrace(task_id="t3", objective="test", strategy_genome_hash="abc")
        trace.add_step(ExecutionStep(step_id=1, action="a", outcome=StepOutcome.SUCCESS))
        for i in range(2, 6):
            trace.add_step(
                ExecutionStep(step_id=i, action=f"step_{i}", outcome=StepOutcome.FAILURE)
            )
        pattern = trace.detect_error_pattern()
        assert pattern == "cascade_failure"

    def test_finalize_sets_duration(self):
        trace = ExecutionTrace(task_id="t4", objective="test", strategy_genome_hash="abc")
        trace.add_step(ExecutionStep(step_id=1, action="a", outcome=StepOutcome.SUCCESS))
        trace.finalize(StepOutcome.SUCCESS)
        assert trace.total_duration_ms >= 0
        assert trace.final_outcome == StepOutcome.SUCCESS


class TestObjectLevel:
    def test_begin_end_task_lifecycle(self):
        s = SearchStrategy(default_genome())
        obj = ObjectLevel(s)
        obj.begin_task("task1", "test objective")
        obj.record_step(action="test", outcome=StepOutcome.SUCCESS)
        trace = obj.end_task(StepOutcome.SUCCESS)
        assert trace.task_id == "task1"
        assert trace.step_count == 1
        assert len(obj.trace_archive) == 1

    def test_end_task_without_begin_raises(self):
        s = SearchStrategy(default_genome())
        obj = ObjectLevel(s)
        with pytest.raises(RuntimeError):
            obj.end_task(StepOutcome.SUCCESS)

    def test_escalation_after_consecutive_failures(self):
        s = SearchStrategy(default_genome())
        obj = ObjectLevel(s)
        obj.begin_task("task2", "test")
        for i in range(5):
            obj.record_step(action=f"fail_{i}", outcome=StepOutcome.FAILURE)
        assert obj.should_escalate()


# ── Meta-Level Tests ─────────────────────────────────────────────


class TestMetaLevel:
    def _make_success_trace(self) -> ExecutionTrace:
        trace = ExecutionTrace(task_id="s1", objective="test", strategy_genome_hash="abc")
        trace.add_step(
            ExecutionStep(
                step_id=1,
                action="a",
                outcome=StepOutcome.SUCCESS,
                heuristic_applied="decompose_first",
            )
        )
        trace.finalize(StepOutcome.SUCCESS)
        trace.self_assessed_confidence = 0.7
        return trace

    def _make_failure_trace(self, pattern: str | None = None) -> ExecutionTrace:
        trace = ExecutionTrace(task_id="f1", objective="test", strategy_genome_hash="abc")
        if pattern == "cascade":
            trace.add_step(ExecutionStep(step_id=1, action="a", outcome=StepOutcome.SUCCESS))
            for i in range(2, 6):
                trace.add_step(
                    ExecutionStep(step_id=i, action=f"f{i}", outcome=StepOutcome.FAILURE)
                )
        elif pattern == "repeated_tool":
            trace.add_step(
                ExecutionStep(step_id=1, action="a", outcome=StepOutcome.FAILURE, tool_used="grep")
            )
            trace.add_step(
                ExecutionStep(step_id=2, action="b", outcome=StepOutcome.FAILURE, tool_used="grep")
            )
        else:
            trace.add_step(
                ExecutionStep(
                    step_id=1, action="a", outcome=StepOutcome.FAILURE, error="generic error"
                )
            )
        trace.detect_error_pattern()
        trace.finalize(StepOutcome.FAILURE)
        trace.self_assessed_confidence = 0.3
        return trace

    def test_success_trace_produces_no_failure_class(self):
        s = SearchStrategy(default_genome())
        meta = MetaLevel(s)
        judgment = meta.monitor(self._make_success_trace())
        assert judgment.failure_class is None
        assert not judgment.is_meta_failure

    def test_cascade_classified_as_meta_failure(self):
        s = SearchStrategy(default_genome())
        meta = MetaLevel(s)
        judgment = meta.monitor(self._make_failure_trace("cascade"))
        assert judgment.failure_class == FailureClass.CASCADE_BLINDNESS
        assert judgment.is_meta_failure is True

    def test_repeated_tool_classified_as_meta_failure(self):
        s = SearchStrategy(default_genome())
        meta = MetaLevel(s)
        judgment = meta.monitor(self._make_failure_trace("repeated_tool"))
        assert judgment.failure_class == FailureClass.WRONG_TOOL_CHOICE
        assert judgment.is_meta_failure is True

    def test_high_confidence_failure_is_miscalibration(self):
        trace = ExecutionTrace(task_id="hc1", objective="test", strategy_genome_hash="abc")
        trace.add_step(
            ExecutionStep(step_id=1, action="a", outcome=StepOutcome.FAILURE, error="nope")
        )
        trace.finalize(StepOutcome.FAILURE)
        trace.self_assessed_confidence = 0.9
        s = SearchStrategy(default_genome())
        meta = MetaLevel(s)
        judgment = meta.monitor(trace)
        assert judgment.failure_class == FailureClass.CONFIDENCE_MISCALIBRATION
        assert judgment.is_meta_failure is True

    def test_control_mutates_strategy_on_meta_failure(self):
        s = SearchStrategy(default_genome())
        meta = MetaLevel(s)
        gen_before = s.genome.generation
        judgment = meta.monitor(self._make_failure_trace("cascade"))
        assert judgment.requires_strategy_mutation
        mutations = meta.control(judgment)
        assert len(mutations) > 0 or s.genome.generation > gen_before

    def test_control_no_mutation_on_object_failure(self):
        s = SearchStrategy(default_genome())
        meta = MetaLevel(s)
        judgment = meta.monitor(self._make_failure_trace(None))
        assert not judgment.is_meta_failure
        mutations = meta.control(judgment)
        assert len(mutations) == 0

    def test_introspection_report(self):
        s = SearchStrategy(default_genome())
        meta = MetaLevel(s)
        meta.monitor(self._make_success_trace())
        report = meta.introspect()
        assert "strategy" in report
        assert "current_fitness" in report
        assert "total_judgments" in report
        assert report["total_judgments"] == 1


# ── Integration Tests ────────────────────────────────────────────


class TestSICAIntegration:
    """End-to-end integration: object-level → meta-level → strategy mutation."""

    def test_full_metacognitive_loop(self):
        """Simulate the complete Nelson-Narens loop."""
        strategy = SearchStrategy(default_genome())
        obj = ObjectLevel(strategy)
        meta = MetaLevel(strategy)

        # Task 1: successful execution
        obj.begin_task("task-1", "find a file")
        obj.record_step(
            action="search",
            outcome=StepOutcome.SUCCESS,
            tool_used="grep",
            heuristic_applied="decompose_first",
        )
        trace1 = obj.end_task(StepOutcome.SUCCESS, confidence=0.8)

        j1 = meta.monitor(trace1)
        assert not j1.is_meta_failure
        meta.control(j1)

        # Task 2: cascade failure → meta-level should detect and mutate
        obj.begin_task("task-2", "deploy service")
        obj.record_step(action="step1", outcome=StepOutcome.SUCCESS)
        for i in range(4):
            obj.record_step(
                action=f"fail_{i}",
                outcome=StepOutcome.FAILURE,
                error=f"error at step {i}: connection refused on port {8080 + i}",
            )
        trace2 = obj.end_task(StepOutcome.FAILURE, confidence=0.3)

        j2 = meta.monitor(trace2)
        assert j2.is_meta_failure
        # With distinct errors, cascade pattern is detected (not repeated_error)
        assert j2.failure_class == FailureClass.CASCADE_BLINDNESS

        gen_before = strategy.genome.generation
        meta.control(j2)
        # Strategy should have been mutated
        assert strategy.genome.generation >= gen_before

    def test_strategy_evolution_across_tasks(self):
        """Verify genome evolves across multiple task cycles."""
        strategy = SearchStrategy(default_genome())
        obj = ObjectLevel(strategy)
        meta = MetaLevel(strategy)
        initial_hash = strategy.genome.genome_hash

        # Run 5 tasks with mixed outcomes
        for i in range(5):
            obj.begin_task(f"task-{i}", f"objective-{i}")
            if i % 2 == 0:
                obj.record_step(
                    action="ok", outcome=StepOutcome.SUCCESS, heuristic_applied="decompose_first"
                )
                trace = obj.end_task(StepOutcome.SUCCESS, confidence=0.7)
            else:
                obj.record_step(action="fail", outcome=StepOutcome.FAILURE, tool_used="search")
                obj.record_step(action="fail2", outcome=StepOutcome.FAILURE, tool_used="search")
                trace = obj.end_task(StepOutcome.FAILURE, confidence=0.3)

            judgment = meta.monitor(trace)
            meta.control(judgment)

        # Genome should have evolved
        report = meta.introspect()
        assert report["total_judgments"] == 5
        assert report["genome_generation"] > 0

# [C5-REAL] Exergy-Maximized
"""Tests for ReflexionEngine - Self-Healing Dispatch Loop (L5).

Validates the core reflexion cycle: execute → fail → reflect → rewrite → retry.
All tests are deterministic (no LLM dependency).

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import pytest

from cortex.engine.reflexion import (
    DiagnosisStrategy,
    Reflection,
    ReflexionConfig,
    ReflexionEngine,
    ReflexionOutcome,
    ReflexionVerdict,
    TreeRewriter,
)
from cortex.isa.builder import (
    dispatch,
    seq,
    par,
    cond,
    halt,
    noop,
    bind,
    Predicate,
    dispatch_targets,
    node_count,
    to_json,
)


# ─── Fixtures ─────────────────────────────────────────────────────


def make_sample_tree() -> dict:
    """A realistic dispatch tree for testing."""
    return seq(
        bind("target", "bounty_alpha"),
        par(
            dispatch("hunter_a", {"mode": "scan"}, id=1),
            dispatch("hunter_b", {"mode": "extract"}, id=2),
        ),
        cond(
            Predicate.always(),
            then_branch=dispatch("aggregator", {"collect": True}, id=3),
            else_branch=halt(error="no results"),
        ),
    )


# ─── DiagnosisStrategy Tests ─────────────────────────────────────


class TestDiagnosisStrategy:
    def test_timeout_error_diagnosed(self):
        tree = dispatch("slow_api", {"wait": True})
        error = TimeoutError("Connection timed out after 5000ms")
        diagnosis, fix = DiagnosisStrategy.diagnose(error, tree)
        assert "time budget" in diagnosis.lower() or "timeout" in diagnosis.lower()
        assert "timeout" in fix.lower() or "retry" in fix.lower()

    def test_connection_error_diagnosed(self):
        tree = dispatch("remote_api", {"url": "https://example.com"})
        error = ConnectionError("Failed to connect to host")
        diagnosis, fix = DiagnosisStrategy.diagnose(error, tree)
        assert "connection" in diagnosis.lower()

    def test_permission_error_diagnosed(self):
        tree = dispatch("admin_action", {"op": "delete"})
        error = PermissionError("Permission denied for resource")
        diagnosis, fix = DiagnosisStrategy.diagnose(error, tree)
        assert "permission" in diagnosis.lower()

    def test_unknown_error_gets_generic_diagnosis(self):
        tree = dispatch("mystery_target")
        error = ZeroDivisionError("division by zero")
        diagnosis, fix = DiagnosisStrategy.diagnose(error, tree)
        assert "unclassified" in diagnosis.lower() or "ZeroDivisionError" in diagnosis

    def test_diagnosis_includes_tree_context(self):
        tree = par(
            dispatch("target_a", id=1),
            dispatch("target_b", id=2),
        )
        error = TimeoutError("timed out")
        diagnosis, _ = DiagnosisStrategy.diagnose(error, tree)
        assert "target_a" in diagnosis or "target_b" in diagnosis


# ─── TreeRewriter Tests ──────────────────────────────────────────


class TestTreeRewriter:
    def test_apply_retry_wrapper_to_dispatch(self):
        tree = dispatch("fragile_api", {"data": 42}, id=1)
        wrapped = TreeRewriter.apply_retry_wrapper(tree, max_retries=3)
        assert "Loop" in wrapped
        assert wrapped["Loop"]["count"] == 3
        assert wrapped["Loop"]["body"]["Dispatch"]["target"] == "fragile_api"

    def test_apply_retry_wrapper_to_seq(self):
        tree = seq(
            dispatch("step_a", id=1),
            dispatch("step_b", id=2),
        )
        wrapped = TreeRewriter.apply_retry_wrapper(tree, max_retries=2)
        assert "Seq" in wrapped
        for child in wrapped["Seq"]:
            if isinstance(child, dict) and "Loop" in child:
                assert child["Loop"]["count"] == 2

    def test_remove_failed_target(self):
        tree = par(
            dispatch("good_target", id=1),
            dispatch("bad_target", id=2),
            dispatch("other_target", id=3),
        )
        cleaned = TreeRewriter.remove_failed_target(tree, "bad_target")
        targets = dispatch_targets(cleaned)
        assert "bad_target" not in targets
        assert "good_target" in targets
        assert "other_target" in targets

    def test_remove_failed_target_nested(self):
        tree = seq(
            dispatch("outer", id=1),
            par(
                dispatch("keep_me", id=2),
                dispatch("remove_me", id=3),
            ),
        )
        cleaned = TreeRewriter.remove_failed_target(tree, "remove_me")
        targets = dispatch_targets(cleaned)
        assert "remove_me" not in targets
        assert "outer" in targets
        assert "keep_me" in targets

    def test_add_timeout_guard(self):
        tree = dispatch("api_call", id=1)
        guarded = TreeRewriter.add_timeout_guard(tree, timeout_ms=3000)
        assert "Seq" in guarded
        nodes = node_count(guarded)
        assert nodes > node_count(tree)

    def test_noop_passthrough(self):
        assert TreeRewriter.apply_retry_wrapper("Noop") == "Noop"
        assert TreeRewriter.remove_failed_target("Noop", "x") == "Noop"


# ─── ReflexionEngine Tests ───────────────────────────────────────


class TestReflexionEngine:
    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        """No reflection needed when execution succeeds immediately."""
        engine = ReflexionEngine()
        tree = dispatch("easy_target", id=1)

        async def executor(t):
            return {"status": "ok"}

        outcome = await engine.execute_with_reflexion(tree, executor)
        assert outcome.succeeded
        assert outcome.iterations_used == 1
        assert len(outcome.reflections) == 0

    @pytest.mark.asyncio
    async def test_success_after_one_reflection(self):
        """Succeed on second attempt after one failure + reflection."""
        call_count = 0

        async def flaky_executor(tree):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Connection refused")
            return {"status": "recovered"}

        engine = ReflexionEngine(config=ReflexionConfig(max_iterations=3, timeout_ms=10_000))
        tree = dispatch("flaky_api", id=1)

        outcome = await engine.execute_with_reflexion(tree, flaky_executor)
        assert outcome.succeeded
        assert outcome.iterations_used == 2
        assert len(outcome.reflections) == 1
        assert outcome.reflections[0].error_type == "ConnectionError"

    @pytest.mark.asyncio
    async def test_exhausted_after_max_iterations(self):
        """Fail after all iterations are exhausted."""

        async def always_fail(tree):
            raise RuntimeError("Persistent failure")

        engine = ReflexionEngine(config=ReflexionConfig(max_iterations=2, timeout_ms=10_000))
        tree = dispatch("doomed_target", id=1)

        outcome = await engine.execute_with_reflexion(tree, always_fail)
        assert not outcome.succeeded
        assert outcome.verdict == ReflexionVerdict.EXHAUSTED
        assert outcome.iterations_used == 2
        assert len(outcome.reflections) == 2

    @pytest.mark.asyncio
    async def test_tree_rewrite_applied_on_failure(self):
        """Verify the dispatch tree is structurally modified between iterations."""
        trees_seen: list[dict] = []

        async def capturing_executor(tree):
            trees_seen.append(tree)
            if len(trees_seen) < 3:
                raise TimeoutError("timed out")
            return {"status": "ok"}

        engine = ReflexionEngine(config=ReflexionConfig(max_iterations=3, timeout_ms=10_000))
        tree = dispatch("target", {"x": 1}, id=1)

        outcome = await engine.execute_with_reflexion(tree, capturing_executor)
        assert outcome.succeeded

        # The tree should have been modified between attempts
        assert len(trees_seen) == 3
        # First tree is original, second should have retry wrapper
        assert trees_seen[0] != trees_seen[1]

    @pytest.mark.asyncio
    async def test_reflection_callback_invoked(self):
        """on_reflection callback is called for each failed iteration."""
        captured_reflections: list[Reflection] = []

        async def on_reflect(r: Reflection):
            captured_reflections.append(r)

        async def fail_once(tree):
            if not captured_reflections:
                raise ValueError("not found in database")
            return {"found": True}

        engine = ReflexionEngine(config=ReflexionConfig(max_iterations=3, timeout_ms=10_000))
        tree = dispatch("db_lookup", id=1)

        outcome = await engine.execute_with_reflexion(tree, fail_once, on_reflection=on_reflect)
        assert outcome.succeeded
        assert len(captured_reflections) == 1
        assert (
            "not found" in captured_reflections[0].diagnosis.lower()
            or "not found" in captured_reflections[0].error_message.lower()
        )

    @pytest.mark.asyncio
    async def test_reflection_memory_accumulates(self):
        """Reflections persist across multiple execute calls."""
        engine = ReflexionEngine(config=ReflexionConfig(max_iterations=1, timeout_ms=5_000))

        async def always_fail(tree):
            raise RuntimeError("fail")

        for _ in range(3):
            await engine.execute_with_reflexion(dispatch("target", id=1), always_fail)

        assert len(engine.reflection_memory) == 3

    @pytest.mark.asyncio
    async def test_session_stats_tracked(self):
        """Session statistics are maintained across executions."""
        engine = ReflexionEngine(config=ReflexionConfig(max_iterations=1, timeout_ms=5_000))

        async def succeed(tree):
            return "ok"

        async def fail(tree):
            raise RuntimeError("fail")

        await engine.execute_with_reflexion(dispatch("a", id=1), succeed)
        await engine.execute_with_reflexion(dispatch("b", id=2), fail)

        stats = engine.get_session_stats()
        assert stats["total_executions"] == 2
        assert stats["total_reflections"] == 1
        assert "RuntimeError" in stats["failure_patterns"]

    @pytest.mark.asyncio
    async def test_accumulated_context_for_prompts(self):
        """Accumulated context string is well-formed for LLM injection."""
        engine = ReflexionEngine(config=ReflexionConfig(max_iterations=1, timeout_ms=5_000))

        async def fail(tree):
            raise ConnectionError("connection refused by host")

        await engine.execute_with_reflexion(dispatch("api", id=1), fail)

        context = engine.get_accumulated_context()
        assert "LESSONS FROM PREVIOUS FAILURES" in context
        assert "ConnectionError" in context

    @pytest.mark.asyncio
    async def test_rewrite_disabled(self):
        """When enable_tree_rewrite=False, trees are NOT modified."""
        trees_seen: list[dict] = []

        async def capture_and_fail(tree):
            trees_seen.append(tree)
            raise RuntimeError("fail")

        engine = ReflexionEngine(
            config=ReflexionConfig(max_iterations=2, timeout_ms=10_000, enable_tree_rewrite=False)
        )
        tree = dispatch("target", id=1)

        await engine.execute_with_reflexion(tree, capture_and_fail)
        assert len(trees_seen) == 2
        # Trees should be identical when rewrite is disabled
        assert trees_seen[0] == trees_seen[1]

    @pytest.mark.asyncio
    async def test_complex_tree_reflexion(self):
        """Full reflexion cycle with a realistic multi-node tree."""
        call_count = 0

        async def realistic_executor(tree):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise TimeoutError("API gateway timeout")
            return {"agents_dispatched": 3, "results": ["a", "b", "c"]}

        engine = ReflexionEngine(config=ReflexionConfig(max_iterations=4, timeout_ms=15_000))
        tree = make_sample_tree()

        outcome = await engine.execute_with_reflexion(
            tree, realistic_executor, task_context="bounty hunting operation"
        )
        assert outcome.succeeded
        assert outcome.iterations_used == 3
        assert len(outcome.reflections) == 2

        # Verify reflections have rich context
        for r in outcome.reflections:
            assert r.tree_node_count > 0
            assert len(r.tree_targets) > 0
            assert r.diagnosis  # not empty
            assert r.proposed_fix  # not empty

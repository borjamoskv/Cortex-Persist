"""Tests for cortex.engine.guard_pipeline.GuardPipeline — fully isolated, no DB.

These tests verify the composable guard/mutator/hook pipeline independently
of the full CortexEngine, proving that guards can be tested in isolation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

# ─── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def pipeline():
    from cortex.engine.guard_pipeline import GuardPipeline

    return GuardPipeline()


@pytest.fixture
def mock_conn():
    """Minimal mock aiosqlite.Connection."""
    return MagicMock()


# ─── Guard Protocol Tests ────────────────────────────────────────────


class TestGuardPipeline:
    async def test_empty_pipeline_passes(self, pipeline, mock_conn):
        """An empty pipeline should not raise."""
        await pipeline.run_guards("test content", "project", "knowledge", {}, mock_conn)

    async def test_passing_guard(self, pipeline, mock_conn):
        """A guard that returns without raising should pass."""
        guard = MagicMock()
        guard.check = AsyncMock(return_value=None)
        pipeline.add_guard(guard)

        await pipeline.run_guards("content", "project", "knowledge", {}, mock_conn)
        guard.check.assert_awaited_once()

    async def test_rejecting_guard_raises(self, pipeline, mock_conn):
        """A guard that raises ValueError should propagate."""
        guard = MagicMock()
        guard.check = AsyncMock(side_effect=ValueError("rejected"))
        pipeline.add_guard(guard)

        with pytest.raises(ValueError, match="rejected"):
            await pipeline.run_guards("content", "project", "knowledge", {}, mock_conn)

    async def test_guard_ordering_preserved(self, pipeline, mock_conn):
        """Guards should execute in registration order."""
        order: list[str] = []

        async def make_guard(name: str):
            async def check(content, project, fact_type, meta, conn, **kw):
                order.append(name)

            g = MagicMock()
            g.check = check
            return g

        g1 = await make_guard("first")
        g2 = await make_guard("second")
        g3 = await make_guard("third")

        pipeline.add_guard(g1)
        pipeline.add_guard(g2)
        pipeline.add_guard(g3)

        await pipeline.run_guards("content", "project", "knowledge", {}, mock_conn)
        assert order == ["first", "second", "third"]

    async def test_first_rejection_stops_chain(self, pipeline, mock_conn):
        """When the first guard rejects, subsequent guards are not called."""
        g1 = MagicMock()
        g1.check = AsyncMock(side_effect=ValueError("blocked"))
        g2 = MagicMock()
        g2.check = AsyncMock(return_value=None)

        pipeline.add_guard(g1)
        pipeline.add_guard(g2)

        with pytest.raises(ValueError, match="blocked"):
            await pipeline.run_guards("content", "project", "knowledge", {}, mock_conn)
        g2.check.assert_not_awaited()


# ─── Mutator Tests ───────────────────────────────────────────────────


class TestMutators:
    async def test_mutator_transforms_content(self, pipeline, mock_conn):
        """A mutator should be able to modify content, fact_type, and meta."""

        async def transform(content, project, fact_type, meta, conn, **kw):
            return content.upper(), "bridge", {**meta, "mutated": True}

        mutator = MagicMock()
        mutator.transform = transform
        pipeline.add_mutator(mutator)

        c, ft, m = await pipeline.run_mutators("hello", "project", "knowledge", {}, mock_conn)
        assert c == "HELLO"
        assert ft == "bridge"
        assert m["mutated"] is True

    async def test_chained_mutators(self, pipeline, mock_conn):
        """Mutators should chain — each receives the previous output."""

        async def add_prefix(content, project, fact_type, meta, conn, **kw):
            return f"[PREFIX] {content}", fact_type, meta

        async def add_suffix(content, project, fact_type, meta, conn, **kw):
            return f"{content} [SUFFIX]", fact_type, meta

        m1, m2 = MagicMock(), MagicMock()
        m1.transform, m2.transform = add_prefix, add_suffix
        pipeline.add_mutator(m1)
        pipeline.add_mutator(m2)

        c, _, _ = await pipeline.run_mutators("body", "project", "knowledge", {}, mock_conn)
        assert c == "[PREFIX] body [SUFFIX]"


# ─── Post-Store Hook Tests ──────────────────────────────────────────


class TestPostHooks:
    async def test_hook_called_after_store(self, pipeline, mock_conn):
        hook = MagicMock()
        hook.on_stored = AsyncMock(return_value=None)
        pipeline.add_post_hook(hook)

        await pipeline.run_post_hooks(123, "project", "knowledge", mock_conn)
        hook.on_stored.assert_awaited_once()

    async def test_failing_hook_does_not_raise(self, pipeline, mock_conn):
        """Post-store hooks must never raise — failures are logged."""
        hook = MagicMock()
        hook.on_stored = AsyncMock(side_effect=RuntimeError("disk on fire"))
        pipeline.add_post_hook(hook)

        # Should NOT raise
        await pipeline.run_post_hooks(123, "project", "knowledge", mock_conn)

    async def test_multiple_hooks_all_run(self, pipeline, mock_conn):
        """All post-store hooks should run, even if one fails."""
        results: list[str] = []

        async def ok_hook(fact_id, project, fact_type, conn, **kw):
            results.append("ok")

        async def bad_hook(fact_id, project, fact_type, conn, **kw):
            results.append("bad")
            raise RuntimeError("boom")

        async def final_hook(fact_id, project, fact_type, conn, **kw):
            results.append("final")

        h1, h2, h3 = MagicMock(), MagicMock(), MagicMock()
        h1.on_stored, h2.on_stored, h3.on_stored = ok_hook, bad_hook, final_hook
        pipeline.add_post_hook(h1)
        pipeline.add_post_hook(h2)
        pipeline.add_post_hook(h3)

        await pipeline.run_post_hooks(123, "project", "knowledge", mock_conn)
        assert results == ["ok", "bad", "final"]


# ─── Count Properties ───────────────────────────────────────────────


class TestCounts:
    def test_empty_counts(self, pipeline):
        assert pipeline.guard_count == 0
        assert pipeline.mutator_count == 0
        assert pipeline.hook_count == 0

    def test_counts_after_registration(self, pipeline):
        pipeline.add_guard(MagicMock())
        pipeline.add_guard(MagicMock())
        pipeline.add_mutator(MagicMock())
        pipeline.add_post_hook(MagicMock())
        pipeline.add_post_hook(MagicMock())
        pipeline.add_post_hook(MagicMock())

        assert pipeline.guard_count == 2
        assert pipeline.mutator_count == 1
        assert pipeline.hook_count == 3

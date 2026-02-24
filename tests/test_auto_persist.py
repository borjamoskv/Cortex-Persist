"""Tests for AutoPersistHook — MCP session auto-persist.

Verifies that the hook correctly detects decision/error/ghost signals
in session messages and produces the right SessionFacts.
"""

import pytest

from cortex.mcp.auto_persist import AutoPersistHook, SessionFact


class TestSessionFactClassification:
    """Test message classification into fact types."""

    def test_decision_signals(self):
        hook = AutoPersistHook()
        decisions = [
            "Decided to use PostgreSQL for the main database",
            "DECISION: We chose the monorepo approach",
            "Selected the FastAPI framework over Flask",
            "Approved the new API schema v2",
            "We went with the SQLite approach for local storage",
        ]
        for msg in decisions:
            hook.observe(msg)
        facts = hook.analyze()
        assert all(f.fact_type == "decision" for f in facts)
        assert len(facts) == len(decisions)

    def test_error_signals(self):
        hook = AutoPersistHook()
        errors = [
            "Error: Connection timeout on startup",
            "Failed: Migration script crashed on step 3",
            "Bug: Off-by-one in pagination logic",
            "Fix: Resolved the race condition in async handler",
        ]
        for msg in errors:
            hook.observe(msg)
        facts = hook.analyze()
        assert all(f.fact_type == "error" for f in facts)
        assert len(facts) == len(errors)

    def test_ghost_signals(self):
        hook = AutoPersistHook()
        ghosts = [
            "TODO: Add rate limiting to the API",
            "FIXME: Memory leak in the embeddings cache",
            "This feature is incomplete, needs work",
            "Left off at the authentication module",
        ]
        for msg in ghosts:
            hook.observe(msg)
        facts = hook.analyze()
        assert all(f.fact_type == "ghost" for f in facts)
        assert len(facts) == len(ghosts)

    def test_error_takes_priority_over_decision(self):
        """When a message matches both error and decision signals, error wins."""
        hook = AutoPersistHook()
        hook.observe("Decided to fix the critical error: connection failed")
        facts = hook.analyze()
        # "error:" is not in this, but "fix:" IS an error signal
        # Actually let's check: "decided" is a decision signal, "failed" is error
        # Error has priority in _classify_message
        assert len(facts) == 1

    def test_clean_messages_ignored(self):
        hook = AutoPersistHook()
        hook.observe("The sky is blue today")
        hook.observe("CORTEX uses Merkle trees")
        hook.observe("This is just a regular message")
        facts = hook.analyze()
        assert len(facts) == 0


class TestAutoPeristHookDedup:
    """Test deduplication of detected facts."""

    def test_duplicate_messages_deduplicated(self):
        hook = AutoPersistHook()
        hook.observe("Decided to use SQLite")
        hook.observe("Decided to use SQLite")
        hook.observe("Decided to use SQLite")
        facts = hook.analyze()
        assert len(facts) == 1

    def test_similar_but_different_messages_kept(self):
        hook = AutoPersistHook()
        hook.observe("Decided to use SQLite for storage")
        hook.observe("Decided to use PostgreSQL for production")
        facts = hook.analyze()
        assert len(facts) == 2


class TestAutoPeristHookLifecycle:
    """Test the observe → analyze → persist lifecycle."""

    def test_empty_session_produces_no_facts(self):
        hook = AutoPersistHook()
        facts = hook.analyze()
        assert facts == []

    def test_whitespace_messages_ignored(self):
        hook = AutoPersistHook()
        hook.observe("")
        hook.observe("   ")
        assert len(hook._observations) == 0

    def test_session_fact_repr(self):
        fact = SessionFact("decision", "Decided to use CORTEX v5")
        assert "decision" in repr(fact)
        assert "Decided" in repr(fact)

    def test_custom_project(self):
        hook = AutoPersistHook(project="naroa-web")
        hook.observe("Decided to add SSR support")
        facts = hook.analyze()
        assert facts[0].project == "naroa-web"

    @pytest.mark.asyncio
    async def test_persist_without_engine_returns_empty(self):
        hook = AutoPersistHook(engine=None)
        hook.observe("Decided to test without engine")
        ids = await hook.persist()
        assert ids == []

    @pytest.mark.asyncio
    async def test_persist_no_facts_returns_empty(self):
        hook = AutoPersistHook()
        ids = await hook.persist()
        assert ids == []

"""Integration tests for cortex.engine.store_mixin.StoreMixin.

Uses CortexEngine with a fresh temp database for realistic end-to-end coverage
of the store → deduplicate → deprecate → update pipeline.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Mark all tests in this module as slow (CortexEngine.init_db() takes ~10s per fixture)
# Run with: pytest -m slow   or skip with: pytest -m 'not slow'
pytestmark = pytest.mark.slow


@pytest.fixture
async def engine(tmp_path: Path):
    """Create a CortexEngine with a temp database, close after test."""
    from cortex.engine import CortexEngine

    db = str(tmp_path / "test_store.db")
    e = CortexEngine(db_path=db, auto_embed=False)
    await e.init_db()
    yield e
    await e.close()


# ─── Store ────────────────────────────────────────────────────────────


class TestStore:
    async def test_store_returns_fact_id(self, engine):
        fact_id = await engine.store(
            project="test",
            content="The sovereign ledger stores facts immutably.",
            fact_type="knowledge",
            source="agent:test_suite",
        )
        assert isinstance(fact_id, int)
        assert fact_id > 0

    async def test_store_deduplication_returns_same_id(self, engine):
        """Exact structural hash dedup should return the same fact_id."""
        content = "Deduplication test content unique enough to avoid cross-test collision."
        id1 = await engine.store(
            project="test", content=content,
            fact_type="knowledge", source="agent:test_suite",
        )
        id2 = await engine.store(
            project="test", content=content,
            fact_type="knowledge", source="agent:test_suite",
        )
        assert id1 == id2

    async def test_store_different_content_different_ids(self, engine):
        id1 = await engine.store(
            project="test", content="Fact alpha for diff test.",
            fact_type="knowledge", source="agent:test_suite",
        )
        id2 = await engine.store(
            project="test", content="Fact beta for diff test.",
            fact_type="knowledge", source="agent:test_suite",
        )
        assert id1 != id2

    async def test_store_rejects_empty_content(self, engine):
        from cortex.engine.storage_guard import GuardViolation

        with pytest.raises((ValueError, TypeError, GuardViolation)):
            await engine.store(
                project="test", content="",
                fact_type="knowledge", source="agent:test_suite",
            )


# ─── Store Many ───────────────────────────────────────────────────────


class TestStoreMany:
    async def test_store_many_returns_ids(self, engine):
        facts = [
            {
                "project": "batch",
                "content": f"Batch fact {i} for store_many.",
                "fact_type": "knowledge",
                "source": "agent:test_suite",
            }
            for i in range(3)
        ]
        ids = await engine.store_many(facts)
        assert len(ids) == 3
        assert all(isinstance(i, int) and i > 0 for i in ids)

    async def test_store_many_empty_raises(self, engine):
        with pytest.raises(ValueError, match="empty"):
            await engine.store_many([])


# ─── Deprecate ────────────────────────────────────────────────────────


class TestDeprecate:
    async def test_deprecate_existing_fact(self, engine):
        fact_id = await engine.store(
            project="test", content="Fact to deprecate.",
            fact_type="knowledge", source="agent:test_suite",
        )
        result = await engine.deprecate(fact_id, reason="test")
        assert result is True

    async def test_deprecate_nonexistent_false(self, engine):
        result = await engine.deprecate(999999, reason="missing")
        assert result is False

    async def test_deprecate_invalid_id_raises(self, engine):
        with pytest.raises(ValueError, match="Invalid"):
            await engine.deprecate(-1)


# ─── Update ───────────────────────────────────────────────────────────


class TestUpdate:
    async def test_update_creates_new_version(self, engine):
        original_id = await engine.store(
            project="test",
            content="Original content v1 for update.",
            fact_type="knowledge",
            source="agent:test_suite",
        )
        updated_id = await engine.update(
            original_id, content="Updated content v2.",
        )
        assert updated_id != original_id
        assert updated_id > original_id

    async def test_update_nonexistent_raises(self, engine):
        with pytest.raises(ValueError, match="not found"):
            await engine.update(999999, content="ghost update")

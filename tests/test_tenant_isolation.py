"""
Tests for Multi-Tenant Isolation.

Verifies that tenant boundaries are enforced across all engine operations:
store, recall, and search. No data should leak between tenants.
"""

import asyncio
import os
import tempfile

import pytest

from cortex.engine import CortexEngine

_db_path: str | None = None
_engine: CortexEngine | None = None
_seeded = False


def _get_engine() -> CortexEngine:
    """Lazily create a shared engine for all tests."""
    global _db_path, _engine, _seeded

    if _engine is not None:
        return _engine

    if not os.environ.get("CORTEX_MASTER_KEY"):
        os.environ["CORTEX_MASTER_KEY"] = (
            "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY="
        )

    handle = tempfile.NamedTemporaryFile(suffix="_tenant.db", delete=False)
    _db_path = handle.name
    handle.close()

    _engine = CortexEngine(_db_path)
    asyncio.run(_engine.init_db())
    return _engine


async def _seed_data(eng: CortexEngine) -> None:
    """Seed test data once."""
    global _seeded
    if _seeded:
        return
    _seeded = True

    await eng.store(
        project="shared-project",
        content="Tenant A secret: budget is $1M",
        tenant_id="tenant-alpha",
    )
    await eng.store(
        project="shared-project",
        content="Tenant B secret: budget is $5M",
        tenant_id="tenant-beta",
    )
    await eng.store(
        project="search-test",
        content="React is the best frontend framework for our team",
        tenant_id="tenant-x",
    )
    await eng.store(
        project="search-test",
        content="Vue.js is the best frontend framework for our team",
        tenant_id="tenant-y",
    )
    await eng.store(
        project="default-test",
        content="No tenant specified, should go to default",
    )
    await eng.store(
        project="isolation-check",
        content="Named tenant private data XYZ789",
        tenant_id="tenant-named",
    )


@pytest.fixture
def engine():
    return _get_engine()


class TestTenantIsolationRecall:
    """Tenant A's facts must not appear in Tenant B's recall."""

    @pytest.mark.asyncio
    async def test_recall_isolated_by_tenant(self, engine):
        await _seed_data(engine)

        facts_a = await engine.recall(
            project="shared-project",
            tenant_id="tenant-alpha",
        )
        facts_b = await engine.recall(
            project="shared-project",
            tenant_id="tenant-beta",
        )

        contents_a = [f.content for f in facts_a]
        contents_b = [f.content for f in facts_b]

        assert any("Tenant A" in c for c in contents_a)
        assert not any("Tenant B" in c for c in contents_a)

        assert any("Tenant B" in c for c in contents_b)
        assert not any("Tenant A" in c for c in contents_b)


class TestTenantIsolationSearch:
    """Text search must respect tenant boundaries."""

    @pytest.mark.asyncio
    async def test_text_search_isolated(self, engine):
        await _seed_data(engine)

        results_x = await engine.search(
            query="frontend framework",
            project="search-test",
            tenant_id="tenant-x",
        )
        results_y = await engine.search(
            query="frontend framework",
            project="search-test",
            tenant_id="tenant-y",
        )

        contents_x = [r["content"] for r in results_x]
        contents_y = [r["content"] for r in results_y]

        assert any("React" in c for c in contents_x)
        assert not any("Vue" in c for c in contents_x)

        assert any("Vue" in c for c in contents_y)
        assert not any("React" in c for c in contents_y)


class TestTenantIsolationDefault:
    """Default tenant behavior — backwards compatibility."""

    @pytest.mark.asyncio
    async def test_default_tenant_works(self, engine):
        await _seed_data(engine)

        results = await engine.recall(
            project="default-test",
            tenant_id="default",
        )
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_default_tenant_isolated_from_named(self, engine):
        await _seed_data(engine)

        default_results = await engine.recall(
            project="isolation-check",
            tenant_id="default",
        )
        default_contents = [r.content for r in default_results]
        assert not any("XYZ789" in c for c in default_contents)

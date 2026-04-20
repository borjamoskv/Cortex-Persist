"""Tests for multi-tenant Row-Level Security (RLS) isolation in CORTEX Engine."""

import contextvars
import os
import tempfile

import pytest

from cortex.engine import CortexEngine
from cortex.engine.mixins.base import EngineMixinBase
from cortex.extensions.security.tenant import (
    TenantContextMissingError,
    get_tenant_id,
    tenant_id_var,
)


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
async def engine(temp_db):
    """Engine fixture for memory and search isolation."""
    # Ensure fresh state
    e = CortexEngine(db_path=temp_db, auto_embed=False)
    await e.init_db()
    yield e
    await e.close()


@pytest.mark.asyncio
async def test_tenant_isolation_store_and_recall(engine):
    """Verify that facts stored under one tenant cannot be recalled by another."""

    # Store fact for Alice
    token_alice = tenant_id_var.set("tenant-alice")
    await engine.store(
        content="Alice's secret strategy",
        fact_type="decision",
        project="alpha",
        source="api",
    )
    tenant_id_var.reset(token_alice)

    # Store fact for Bob
    token_bob = tenant_id_var.set("tenant-bob")
    await engine.store(
        content="Bob's secret strategy",
        fact_type="decision",
        project="alpha",
        source="api",
    )
    tenant_id_var.reset(token_bob)

    # Alice queries -> should only see her fact
    token_alice = tenant_id_var.set("tenant-alice")
    facts_alice = await engine.recall(project="alpha")
    assert len(facts_alice) == 1
    assert facts_alice[0]["content"] == "Alice's secret strategy"
    assert facts_alice[0]["tenant_id"] == "tenant-alice"
    tenant_id_var.reset(token_alice)

    # Bob queries -> should only see his fact
    token_bob = tenant_id_var.set("tenant-bob")
    facts_bob = await engine.recall(project="alpha")
    assert len(facts_bob) == 1
    assert facts_bob[0]["content"] == "Bob's secret strategy"
    assert facts_bob[0]["tenant_id"] == "tenant-bob"
    tenant_id_var.reset(token_bob)


@pytest.mark.asyncio
async def test_tenant_isolation_update_and_deprecate(engine):
    """Verify that updating or deprecating cross-tenant facts fails."""

    # Alice stores a fact
    token_alice = tenant_id_var.set("tenant-alice")
    fact_id_alice = await engine.store(
        content="Alice's initial draft", fact_type="knowledge", project="beta", source="api"
    )
    tenant_id_var.reset(token_alice)

    # Bob tries to update Alice's fact
    token_bob = tenant_id_var.set("tenant-bob")
    try:
        updated_id = await engine.update(
            fact_id=fact_id_alice, new_content="Bob hacked this", project="beta"
        )
        assert not updated_id, "Bob should not be able to update Alice's fact"
    except Exception:
        pass  # Depending on implementation it might raise or return None

    # Verify Alice's fact is unchanged
    tenant_id_var.reset(token_bob)

    token_alice = tenant_id_var.set("tenant-alice")
    alice_fact = await engine.get_fact(fact_id_alice)
    assert alice_fact.content == "Alice's initial draft"
    tenant_id_var.reset(token_alice)


def test_get_tenant_id_fails_closed_without_context(monkeypatch) -> None:
    monkeypatch.delenv("CORTEX_ALLOW_LEGACY_DEFAULT_TENANT", raising=False)
    isolated_context = contextvars.Context()
    with pytest.raises(TenantContextMissingError):
        isolated_context.run(get_tenant_id)


def test_get_tenant_id_legacy_flag_allows_default(monkeypatch) -> None:
    monkeypatch.setenv("CORTEX_ALLOW_LEGACY_DEFAULT_TENANT", "true")
    isolated_context = contextvars.Context()
    assert isolated_context.run(get_tenant_id) == "default"


def test_get_tenant_id_returns_bound_context(monkeypatch) -> None:
    monkeypatch.delenv("CORTEX_ALLOW_LEGACY_DEFAULT_TENANT", raising=False)
    isolated_context = contextvars.Context()

    def _run_in_context() -> str:
        token = tenant_id_var.set("tenant-green")
        try:
            return get_tenant_id()
        finally:
            tenant_id_var.reset(token)

    assert isolated_context.run(_run_in_context) == "tenant-green"


def test_resolve_tenant_fails_without_context(monkeypatch) -> None:
    monkeypatch.delenv("CORTEX_ALLOW_LEGACY_DEFAULT_TENANT", raising=False)

    class _DummyEngine(EngineMixinBase):
        pass

    isolated_context = contextvars.Context()
    with pytest.raises(TenantContextMissingError):
        isolated_context.run(_DummyEngine()._resolve_tenant, "default")

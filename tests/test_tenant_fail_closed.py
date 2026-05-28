from __future__ import annotations

import pytest

from cortex.engine import CortexEngine
from cortex.extensions.security.tenant import MissingTenantContext, get_tenant_id, tenant_id_var


def test_get_tenant_id_fails_without_context(monkeypatch) -> None:
    monkeypatch.delenv("CORTEX_LEGACY_DEFAULT_TENANT", raising=False)
    token = tenant_id_var.set(None)
    try:
        with pytest.raises(MissingTenantContext):
            get_tenant_id()
    finally:
        tenant_id_var.reset(token)


def test_get_tenant_id_legacy_default_requires_explicit_flag(monkeypatch) -> None:
    monkeypatch.setenv("CORTEX_LEGACY_DEFAULT_TENANT", "1")
    token = tenant_id_var.set(None)
    try:
        assert get_tenant_id() == "default"
    finally:
        tenant_id_var.reset(token)


@pytest.mark.asyncio
async def test_engine_store_without_tenant_context_fails(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("CORTEX_LEGACY_DEFAULT_TENANT", raising=False)
    token = tenant_id_var.set(None)
    engine = CortexEngine(tmp_path / "tenant.db")
    try:
        with pytest.raises(ValueError, match="Tenant context missing"):
            await engine.store(
                project="audit",
                content="tenant context must be explicit",
                fact_type="knowledge",
            )
    finally:
        tenant_id_var.reset(token)
        await engine.close()

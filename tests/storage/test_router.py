# [C5-REAL] Exergy-Maximized
"""
Tests for the TenantRouter, including the new LOCAL_SHARDED storage mode.
"""

from __future__ import annotations

import os
import shutil
import pytest
from pathlib import Path

from legacy_research.storage import StorageMode
from legacy_research.storage.router import TenantRouter, get_router


@pytest.fixture
def clean_shard_dir(tmp_path, monkeypatch):
    """Fixture to mock DB_PATH and SHARD_DIR to use temporary directory."""
    db_file = tmp_path / "cortex_test.db"
    shard_dir = tmp_path / "shards"
    
    monkeypatch.setenv("CORTEX_DB", str(db_file))
    monkeypatch.setenv("CORTEX_SHARD_DIR", str(shard_dir))
    
    # Reload config to pick up env variables
    from legacy_research.config import reload
    reload()
    
    yield db_file, shard_dir


@pytest.mark.asyncio
async def test_router_local_mode(clean_shard_dir, monkeypatch) -> None:
    """Verify that LOCAL storage mode returns the same shared pool for all tenants."""
    monkeypatch.setenv("CORTEX_STORAGE", "local")
    
    router = TenantRouter()
    assert router.mode == StorageMode.LOCAL
    
    # Get backend for tenant A and tenant B
    backend_a = await router.get_backend(tenant_id="tenant-a")
    backend_b = await router.get_backend(tenant_id="tenant-b")
    
    # They should be the exact same connection pool
    assert backend_a is backend_b
    assert "local" in router.active_tenants
    
    await router.close_all()


@pytest.mark.asyncio
async def test_router_local_sharded_mode(clean_shard_dir, monkeypatch) -> None:
    """Verify that LOCAL_SHARDED mode routes tenants to separate isolated SQLite DB files."""
    db_file, shard_dir = clean_shard_dir
    monkeypatch.setenv("CORTEX_STORAGE", "local_sharded")
    
    router = TenantRouter()
    assert router.mode == StorageMode.LOCAL_SHARDED
    
    # Get backend for tenant A and tenant B
    backend_a = await router.get_backend(tenant_id="tenant-a")
    backend_b = await router.get_backend(tenant_id="tenant-b")
    
    # They must be separate connection pool instances
    assert backend_a is not backend_b
    
    # Shard paths must exist
    shard_a_path = shard_dir / "cortex_test_tenant-a.db"
    shard_b_path = shard_dir / "cortex_test_tenant-b.db"
    
    assert shard_a_path.exists()
    assert shard_b_path.exists()
    
    assert "tenant-a" in router.active_tenants
    assert "tenant-b" in router.active_tenants
    
    await router.close_all()


@pytest.mark.asyncio
async def test_router_eviction(clean_shard_dir, monkeypatch) -> None:
    """Verify that connections are evicted when the connection limit is reached."""
    monkeypatch.setenv("CORTEX_STORAGE", "local_sharded")
    
    # Temporarily set max backends to a very small number for testing eviction
    import legacy_research.storage.router
    monkeypatch.setattr(cortex.storage.router, "_MAX_BACKENDS", 2)
    
    router = TenantRouter()
    
    backend_a = await router.get_backend(tenant_id="tenant-a")
    backend_b = await router.get_backend(tenant_id="tenant-b")
    assert len(router.active_tenants) == 2
    
    # Requesting tenant-c should evict tenant-a (the oldest)
    backend_c = await router.get_backend(tenant_id="tenant-c")
    assert len(router.active_tenants) == 2
    assert "tenant-a" not in router.active_tenants
    assert "tenant-b" in router.active_tenants
    assert "tenant-c" in router.active_tenants
    
    await router.close_all()

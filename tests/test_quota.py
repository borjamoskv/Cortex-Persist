"""Tests para CORTEX Sovereign Quota Manager."""

import asyncio
import time

import pytest

from cortex.llm.quota import SovereignQuotaManager


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "quota_test.db"
    yield str(db_file)
    if db_file.exists():
        db_file.unlink()


def test_quota_manager_init(temp_db):
    mgr = SovereignQuotaManager(db_path=temp_db, capacity=10, refill_rate=1.0)
    stats = mgr.status()
    assert stats.capacity == 10
    assert stats.current_tokens == 10.0


@pytest.mark.asyncio
async def test_quota_manager_acquire_and_refill(temp_db):
    mgr = SovereignQuotaManager(db_path=temp_db, capacity=2, refill_rate=10.0)

    # Consumir 2 tokens (debería ser instantáneo)
    assert await mgr.acquire(tokens=2) is True

    stats = mgr.status()
    assert stats.current_tokens < 1.0  # Casi 0

    # Consumir 1 token más (debería dormir ~0.1s para recargar 1 token a 10 t/s)
    start = time.time()
    assert await mgr.acquire(tokens=1) is True
    elapsed = time.time() - start
    assert elapsed >= 0.05  # Dejó respirar al sistema


@pytest.mark.asyncio
async def test_quota_manager_concurrency(temp_db):
    """Test para simular múltiples procesos/coroutines compitiendo por cuota."""
    # Capacidad pequeña, relleno muy rápido para no hacer el test lento,
    # pero obligar a la sincronidad SQLite a funcionar
    mgr = SovereignQuotaManager(db_path=temp_db, capacity=5, refill_rate=100.0)

    async def worker():
        await mgr.acquire(tokens=1)
        return True

    results = await asyncio.gather(*(worker() for _ in range(20)))
    assert len(results) == 20
    assert all(results)

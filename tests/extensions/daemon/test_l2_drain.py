import pytest
import time
from unittest.mock import AsyncMock, MagicMock
from babylon60.extensions.daemon.monitors.l2_drain import L2DrainMonitor, MAX_AGE_SECONDS


@pytest.mark.asyncio
async def test_l2_drain_monitor_success():
    engine_mock = AsyncMock()
    conn_mock = AsyncMock()
    engine_mock.get_conn.return_value = conn_mock

    # Mocking rows: fact_id, tenant_id, embedding_blob
    # using a simple json string blob for the test
    conn_mock.execute.side_effect = [
        AsyncMock(fetchone=AsyncMock(return_value=None)),  # ouroboros hook
        AsyncMock(fetchall=AsyncMock(return_value=[(1, "tenant_a", b"[0.1, 0.2]")])),
        AsyncMock(fetchone=AsyncMock(return_value=("[0.1, 0.2]",))),  # vec_to_json
        AsyncMock(),  # delete fact_embeddings
        AsyncMock(),  # update facts
    ]

    monitor = L2DrainMonitor(projects=["test_project"], interval_seconds=10, engine=engine_mock)

    backend_mock = AsyncMock()
    monitor._backend = backend_mock

    alerts = await monitor.check_async()

    assert len(alerts) == 1
    assert alerts[0].reduction == 1
    assert "1 vectores movidos" in alerts[0].message

    # Verify backend called
    backend_mock.upsert.assert_called_once_with(
        fact_id=1, embedding=[0.1, 0.2], tenant_id="tenant_a", payload={"project": "test_project"}
    )


@pytest.mark.asyncio
async def test_l2_drain_monitor_no_rows():
    engine_mock = AsyncMock()
    conn_mock = AsyncMock()
    engine_mock.get_conn.return_value = conn_mock

    conn_mock.execute.return_value = AsyncMock(fetchall=AsyncMock(return_value=[]))

    monitor = L2DrainMonitor(projects=["test_project"], interval_seconds=10, engine=engine_mock)
    monitor._backend = AsyncMock()

    alerts = await monitor.check_async()
    assert len(alerts) == 0

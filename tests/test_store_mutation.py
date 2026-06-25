
# [C5-REAL] Exergy-Maximized
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from cortex.engine.store_mutation import (
    deprecate_impl_logic,
    invalidate_impl_logic,
    purge_logic,
    _fetch_fact_state,
)
import aiosqlite





@pytest.mark.asyncio
async def test_deprecate_impl_logic_success():
    mock_conn = MagicMock(spec=aiosqlite.Connection)
    mock_conn.execute = AsyncMock()
    mock_conn.commit = AsyncMock()

    mock_mixin = MagicMock()
    mock_mixin._log_transaction = AsyncMock()

    with (
        patch(
            "cortex.engine.store_mutation._fetch_fact_state",
            return_value=(1, "knowledge", None, 0, 0),
        ) as mock_fetch,
        patch("cortex.engine.store_mutation.AsyncCausalGraph") as mock_graph,
    ):
        mock_graph_instance = mock_graph.return_value
        mock_graph_instance.propagate_taint = AsyncMock()

        result = await deprecate_impl_logic(
            mixin_instance=mock_mixin,
            conn=mock_conn,
            fact_id=1,
            reason="test_reason",
            tenant_id="tenant1",
        )

        assert result is True
        mock_conn.execute.assert_called_once()
        mock_mixin._log_transaction.assert_called_once()
        mock_graph_instance.propagate_taint.assert_called_once()


@pytest.mark.asyncio
async def test_invalidate_impl_logic_success():
    mock_conn = MagicMock(spec=aiosqlite.Connection)
    mock_conn.execute = AsyncMock()
    mock_conn.commit = AsyncMock()

    mock_mixin = MagicMock()
    mock_mixin._log_transaction = AsyncMock()

    with (
        patch(
            "cortex.engine.store_mutation._fetch_fact_state",
            return_value=(1, "knowledge", None, 0, 0),
        ) as mock_fetch,
        patch("cortex.engine.store_mutation.AsyncCausalGraph") as mock_graph,
    ):
        mock_graph_instance = mock_graph.return_value
        mock_graph_instance.propagate_taint = AsyncMock()

        result = await invalidate_impl_logic(
            mixin_instance=mock_mixin,
            conn=mock_conn,
            fact_id=1,
            reason="test_invalid",
            tenant_id="tenant1",
        )

        assert result is True
        mock_conn.execute.assert_called_once()
        mock_mixin._log_transaction.assert_called_once()
        mock_graph_instance.propagate_taint.assert_called_once()


@pytest.mark.asyncio
async def test_purge_logic_success():
    mock_conn = MagicMock(spec=aiosqlite.Connection)
    mock_conn.commit = AsyncMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_cursor.fetchone = AsyncMock(side_effect=[(0,), ("hash123", "tx456")])

    async def mock_execute(*args, **kwargs):
        return mock_cursor

    mock_conn.execute = mock_execute

    class MockContext:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_mixin = MagicMock()
    mock_mixin.session.return_value = MockContext()
    mock_mixin._log_transaction = AsyncMock()

    with patch(
        "cortex.engine.store_mutation._fetch_fact_state", return_value=(1, "knowledge", None, 0, 0)
    ) as mock_fetch:
        result = await purge_logic(
            mixin_instance=mock_mixin, fact_id=1, tenant_id="tenant1", force=False
        )

        assert result is True
        mock_mixin._log_transaction.assert_called_once()

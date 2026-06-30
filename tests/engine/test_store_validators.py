# [C5-REAL] Exergy-Maximized

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from babylon60.engine.core.store_validators import validate_content, check_dedup


def test_validate_content_decision_replacement():
    """Test that validate_content correctly replaces duplicate DECISION: prefix for decision fact types."""
    # Case 1: fact_type="decision" and starts with "DECISION: DECISION:"
    content = "DECISION: DECISION: Proceed with the plan."
    normalized = validate_content("project1", content, "decision")
    assert normalized == "DECISION: Proceed with the plan."

    # Case 2: fact_type="decision" but normal content
    content2 = "DECISION: We should wait."
    normalized2 = validate_content("project1", content2, "decision")
    assert normalized2 == "DECISION: We should wait."

    # Case 3: fact_type is not "decision" but starts with "DECISION: DECISION:"
    content3 = "DECISION: DECISION: Wait, what?"
    normalized3 = validate_content("project1", content3, "thought")
    assert normalized3 == "DECISION: DECISION: Wait, what?"

    # Case 4: Any other string
    content4 = "Just a regular memory fact."
    normalized4 = validate_content("project1", content4, "memory")
    assert normalized4 == "Just a regular memory fact."


@pytest.mark.asyncio
async def test_check_dedup_found():
    """Test check_dedup returns an existing ID if found."""
    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = (42,)

    mock_conn = MagicMock()
    mock_ctx_mgr = MagicMock()
    mock_ctx_mgr.__aenter__.return_value = mock_cursor
    mock_ctx_mgr.__aexit__ = AsyncMock()
    mock_conn.execute.return_value = mock_ctx_mgr

    tenant_id = "tenant_1"
    project = "proj_alpha"
    content = "Some unique fact content"

    with patch("cortex.utils.canonical.compute_fact_hash", return_value="fake_hash") as mock_hash:
        result = await check_dedup(mock_conn, tenant_id, project, content)

    mock_hash.assert_called_once_with(content)
    assert result == 42

    call_args = mock_conn.execute.call_args
    query, params = call_args[0]
    assert "SELECT id FROM facts" in query
    assert params == (tenant_id, project, "fake_hash")


@pytest.mark.asyncio
async def test_check_dedup_not_found():
    """Test check_dedup returns None if no duplicate is found."""
    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = None

    mock_conn = MagicMock()
    mock_ctx_mgr = MagicMock()
    mock_ctx_mgr.__aenter__.return_value = mock_cursor
    mock_ctx_mgr.__aexit__ = AsyncMock()
    mock_conn.execute.return_value = mock_ctx_mgr

    tenant_id = "tenant_1"
    project = "proj_alpha"
    content = "Some new content"

    result = await check_dedup(mock_conn, tenant_id, project, content)

    assert result is None


@pytest.mark.asyncio
async def test_check_dedup_with_exclude_id():
    """Test check_dedup appends the exclude_id to query and params."""
    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = (99,)

    mock_conn = MagicMock()
    mock_ctx_mgr = MagicMock()
    mock_ctx_mgr.__aenter__.return_value = mock_cursor
    mock_ctx_mgr.__aexit__ = AsyncMock()
    mock_conn.execute.return_value = mock_ctx_mgr

    tenant_id = "tenant_1"
    project = "proj_alpha"
    content = "Updated content"

    with patch("cortex.utils.canonical.compute_fact_hash", return_value="hash_99"):
        result = await check_dedup(mock_conn, tenant_id, project, content, exclude_id=10)

    assert result == 99

    call_args = mock_conn.execute.call_args
    query, params = call_args[0]
    assert "AND id != ?" in query
    assert params == (tenant_id, project, "hash_99", 10)

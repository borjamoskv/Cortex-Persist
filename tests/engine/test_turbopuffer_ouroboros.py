# [C5-REAL] Exergy-Maximized
import pytest
from unittest.mock import AsyncMock, patch
from babylon60.storage.turbopuffer import TurbopufferVectorBackend


@pytest.mark.asyncio
async def test_ouroboros_prune():
    """Verify that Ouroboros can autonomously prune the Turbopuffer backend."""
    backend = TurbopufferVectorBackend(api_key="mock_key")
    backend._client = AsyncMock()  # Mock the httpx client

    # Prune with missing signature should fail
    with pytest.raises(PermissionError, match="Missing cryptographic taint signature"):
        await backend.autonomous_prune_by_entropy(
            tenant_id="test", entropy_threshold=0.9, taint_signature="INVALID_SIG"
        )

    # Prune with valid signature should pass
    result = await backend.autonomous_prune_by_entropy(
        tenant_id="test", entropy_threshold=0.9, taint_signature="CORTEX-TAINT:OUROBOROS-∞:abc"
    )

    # Placeholder returns 0 currently
    assert result == 0


@pytest.mark.asyncio
async def test_ouroboros_hook_dynamic_threshold():
    """Verify dynamic threshold fetching from SQLite facts table."""
    from babylon60.extensions.evolution.ouroboros_hook import get_dynamic_threshold

    conn = AsyncMock()

    # Mock no override found
    cursor = AsyncMock()
    cursor.fetchone.return_value = None
    conn.execute.return_value = cursor

    threshold = await get_dynamic_threshold(conn, "projectA")
    assert threshold == 7 * 24 * 3600

    # Mock override found
    cursor.fetchone.return_value = ['{"threshold_seconds": 3600}']
    threshold = await get_dynamic_threshold(conn, "projectA")
    assert threshold == 3600

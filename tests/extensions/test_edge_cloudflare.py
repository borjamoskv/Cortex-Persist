import pytest
from unittest.mock import patch, MagicMock
from cortex.extensions.edge_cloudflare.edge_bridge import CloudflareEdgeBridge

@pytest.mark.asyncio
async def test_cloudflare_edge_bridge_sync():
    """Verify Edge Bridge initializes and simulates sync deterministically when no db id."""
    bridge = CloudflareEdgeBridge(account_id="test_acc", api_token="test_token")
    assert bridge.account_id == "test_acc"
    assert bridge.base_url == "https://api.cloudflare.com/client/v4/accounts/test_acc/d1/database"
    
    # Test sync simulation
    result = await bridge.sync_ledger_to_edge(taint="ZK-001", payload_hash="abcd123", payload="data")
    assert result is True
    await bridge.close()

@pytest.mark.asyncio
async def test_cloudflare_edge_bridge_real_sync():
    """Verify Edge Bridge attempts HTTP when db id provided."""
    bridge = CloudflareEdgeBridge(account_id="test_acc", api_token="test_token", database_id="db123")
    assert bridge.base_url == "https://api.cloudflare.com/client/v4/accounts/test_acc/d1/database/db123/query"
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        result = await bridge.sync_ledger_to_edge(taint="ZK-001", payload_hash="abcd123", payload="data")
        assert result is True
        mock_post.assert_called_once()
        
    await bridge.close()

@pytest.mark.asyncio
async def test_cloudflare_edge_bridge_verify():
    """Verify cryptographic signature check fallback."""
    bridge = CloudflareEdgeBridge(account_id="test_acc", api_token="test_token")
    assert bridge.verify_edge_signature("v1_edge_12345") is True
    assert bridge.verify_edge_signature("invalid") is False
    assert bridge.verify_edge_signature("sig1234567") is True
    await bridge.close()

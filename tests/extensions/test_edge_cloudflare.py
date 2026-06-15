import pytest
from cortex.extensions.edge_cloudflare.edge_bridge import CloudflareEdgeBridge

@pytest.mark.asyncio
async def test_cloudflare_edge_bridge_sync():
    """Verify Edge Bridge initializes and simulates sync deterministically."""
    bridge = CloudflareEdgeBridge(account_id="test_acc", api_token="test_token")
    assert bridge.account_id == "test_acc"
    assert bridge.base_url == "https://api.cloudflare.com/client/v4/accounts/test_acc/d1/database"
    
    # Test sync simulation
    result = await bridge.sync_ledger_to_edge(taint="ZK-001", payload_hash="abcd123")
    assert result is True

def test_cloudflare_edge_bridge_verify():
    """Verify cryptographic signature check fallback."""
    bridge = CloudflareEdgeBridge(account_id="test_acc", api_token="test_token")
    assert bridge.verify_edge_signature("sig12345") is True

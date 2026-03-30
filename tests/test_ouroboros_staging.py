import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from cortex.infrastructure.anvil_node import AnvilStagingNode
from cortex.extensions.wealth.mev_validator import MEVValidator


@pytest.mark.asyncio
async def test_mev_validator_staging_node():
    anvil = AnvilStagingNode(port=8545)
    validator = MEVValidator(anvil)
    
    payload = {"signed_txs": ["0xdeadbeef"]}
    
    # Mock httpx response
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # 1. Success validation
        class MockResponse:
            status_code = 200
        mock_post.return_value = MockResponse()
        
        is_valid = await validator.simulate_bundle(payload)
        assert is_valid is True
        
        # 2. KV Routing hit (should skip httpx)
        mock_post.reset_mock()
        is_valid_cached = await validator.simulate_bundle(payload)
        assert is_valid_cached is True
        mock_post.assert_not_called()
        
        # 3. Structural abort (Atomicity fail)
        bad_payload = {"signed_txs": []}
        is_valid_bad = await validator.simulate_bundle(bad_payload)
        assert is_valid_bad is False

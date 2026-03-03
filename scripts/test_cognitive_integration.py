import asyncio
import logging
import json
from unittest.mock import MagicMock, AsyncMock
from cortex.moltbook.client import MoltbookClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_integration")

async def test_auto_verification():
    # Mock LLM
    mock_llm = AsyncMock()
    # Mock a response from LLM for the challenge
    mock_llm.complete.return_value = '{"num1": 20.0, "num2": 5.0, "op": "-"}'
    
    client = MoltbookClient(api_key="test_key", llm=mock_llm, stealth=False)
    
    # Mock the internal _client.request to return a challenge first, then a success
    original_request = client._client.request
    
    challenge_json = {
        "success": True,
        "verification_required": True,
        "verification": {
            "verification_code": "test_code",
            "challenge_text": "A] lO^bSt-Er S[wImS aT/ tW]eNn-Tyy mE^tE[rS aNd] SlO/wS bY^ fI[vE",
            "expires_at": "2026-03-03T12:00:00Z"
        },
        "post": {"id": "test_post_id", "title": "Test"}
    }
    
    verify_success_json = {
        "success": True,
        "message": "Verified!",
        "content_id": "test_post_id"
    }

    call_count = 0
    async def mock_request(method, url, **kwargs):
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        resp.headers = {}
        if "/verify" in url:
            resp.status_code = 200
            resp.json.return_value = verify_success_json
        else:
            resp.status_code = 200
            resp.json.return_value = challenge_json
        return resp

    client._client.request = mock_request
    
    print("Starting autoverification test...")
    result = await client.create_post("general", "Hello")
    
    print(f"Result: {json.dumps(result, indent=2)}")
    
    assert result["verification_required"] is True
    assert "verification_result" in result
    assert result["verification_result"]["success"] is True
    
    print("✅ Test passed: Challenge was automatically detected and solved via LLM mock.")

if __name__ == "__main__":
    asyncio.run(test_auto_verification())

# [C5-REAL] Exergy-Maximized
import json
import os
import pytest
from unittest.mock import patch, MagicMock

from cortex.mcp_server.apollo_tools import register_apollo_tools


class MockFastMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def mock_mcp():
    mcp = MockFastMCP()
    register_apollo_tools(mcp)
    return mcp


@patch.dict(os.environ, {"APOLLO_API_KEY": "fake_c5_real_key"})
@patch("cortex.mcp_server.apollo_tools.requests.post")
def test_apollo_extract_leads_success(mock_post, mock_mcp, tmp_path):
    # Mock response from Apollo
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "contacts": [
            {
                "name": "Satoshi Nakamoto",
                "title": "Founder",
                "organization_name": "Bitcoin",
                "email": "satoshi@bitcoin.org",
                "linkedin_url": "https://linkedin.com/in/satoshi",
            },
            {
                "name": "Vitalik Buterin",
                "title": "Co-Founder",
                "organization_name": "Ethereum",
                "email": "vitalik@ethereum.org",
                "linkedin_url": "https://linkedin.com/in/vitalik",
            },
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    # Change working directory to tmp_path for the test so it writes there
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        # Call the tool
        tool_func = mock_mcp.tools["cortex_apollo_extract_leads"]
        result = tool_func(target_leads=2, output_filename="test_apollo.json")

        assert "✅ C5-REAL Lead Extraction complete" in result

        # Verify the file was written
        with open("test_apollo.json") as f:
            data = json.load(f)

        assert len(data) == 2
        assert data[0]["Name"] == "Satoshi Nakamoto"
        assert data[1]["Company"] == "Ethereum"

    finally:
        os.chdir(original_cwd)


@patch.dict(os.environ, clear=True)
def test_apollo_extract_leads_missing_key(mock_mcp):
    # Ensure APOLLO_API_KEY is not set
    tool_func = mock_mcp.tools["cortex_apollo_extract_leads"]
    result = tool_func(target_leads=2)

    assert "❌ Rejected: APOLLO_API_KEY" in result

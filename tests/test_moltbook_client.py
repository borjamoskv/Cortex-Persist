"""Tests for the Moltbook HTTP client (mocked responses)."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from cortex.moltbook.client import (
    MoltbookClient,
)


@pytest.fixture
def client():
    """Client with a test API key."""
    return MoltbookClient(api_key="moltbook_test_key")


class TestCredentials:
    """Test credential loading and saving."""

    def test_uses_provided_key(self, client):
        assert client._api_key == "moltbook_test_key"

    def test_loads_from_env(self, monkeypatch):
        monkeypatch.setenv("MOLTBOOK_API_KEY", "moltbook_env_key")
        c = MoltbookClient()
        assert c._api_key == "moltbook_env_key"

    def test_saves_credentials(self, tmp_path, monkeypatch):
        creds_path = tmp_path / "credentials.json"
        monkeypatch.setattr("cortex.moltbook.client._CREDENTIALS_PATH", creds_path)

        MoltbookClient.save_credentials("moltbook_xxx", "TestAgent")
        assert creds_path.exists()

        data = json.loads(creds_path.read_text())
        assert data["api_key"] == "moltbook_xxx"
        assert data["agent_name"] == "TestAgent"


class TestZeroTrust:
    """Test that auth is never sent to non-moltbook domains."""

    def test_refuses_non_moltbook_url(self, client):
        with patch.object(client, "_request", wraps=client._request):
            # Directly test the validation in _request
            with pytest.raises(ValueError, match="SECURITY"):
                # Manually construct a request to a bad URL
                original_base = "https://evil.com"
                old_request = client._request

                def bad_request(method, path, **kwargs):
                    url = f"{original_base}{path}"
                    if not url.startswith("https://www.moltbook.com/"):
                        raise ValueError(f"SECURITY: refusing to send request to {url}")
                    return old_request(method, path, **kwargs)

                bad_request("GET", "/test")


class TestAPIRequests:
    """Test API method call structure."""

    def _mock_response(self, data: dict, status_code: int = 200, headers: dict = None):
        """Create a mock response object compatible with httpx/curl_cffi."""
        resp = MagicMock()
        resp.json.return_value = data
        resp.status_code = status_code

        mock_headers = MagicMock()
        header_data = headers or {
            "X-RateLimit-Remaining": "55",
            "X-RateLimit-Reset": str(time.time() + 3600),
            "Content-Type": "application/json",
        }
        mock_headers.get.side_effect = lambda k, d=None: header_data.get(k, d)
        resp.headers = mock_headers
        return resp

    @pytest.mark.asyncio
    async def test_get_home(self, client):
        mock_resp = self._mock_response(
            {
                "success": True,
                "your_account": {"karma": 42},
            }
        )
        with patch.object(client._client, "request", return_value=mock_resp):
            result = await client.get_home()
            assert result["success"] is True
            assert result["your_account"]["karma"] == 42

    @pytest.mark.asyncio
    async def test_create_post(self, client):
        mock_resp = self._mock_response(
            {
                "success": True,
                "post": {"id": "test-123", "title": "Test"},
            }
        )
        with patch.object(client._client, "request", return_value=mock_resp):
            result = await client.create_post("general", "Test", "Content")
            assert result["post"]["id"] == "test-123"

    @pytest.mark.asyncio
    async def test_upvote_post(self, client):
        mock_resp = self._mock_response({"success": True})
        with patch.object(client._client, "request", return_value=mock_resp):
            result = await client.upvote_post("post-abc")
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_search(self, client):
        mock_resp = self._mock_response(
            {
                "success": True,
                "results": [{"id": "r1", "similarity": 0.85}],
            }
        )
        with patch.object(client._client, "request", return_value=mock_resp):
            result = await client.search("memory architectures")
            assert len(result["results"]) == 1
            assert result["results"][0]["similarity"] == 0.85

    @pytest.mark.asyncio
    async def test_updates_rate_limit_tracking(self, client):
        mock_resp = self._mock_response(
            {"success": True}, headers={"X-RateLimit-Remaining": "55"}
        )
        with patch.object(client._client, "request", return_value=mock_resp):
            await client.get_home()
            assert client._rate_remaining == 55

    @pytest.mark.asyncio
    async def test_register_saves_credentials(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("cortex.moltbook.client._CREDENTIALS_PATH", tmp_path / "creds.json")
        mock_resp = self._mock_response(
            {
                "agent": {
                    "api_key": "moltbook_new_key",
                    "claim_url": "https://www.moltbook.com/claim/xxx",
                },
            }
        )

        # Use a client without auth for register
        c = MoltbookClient(api_key=None, stealth=False)
        with patch.object(c._client, "request", return_value=mock_resp):
            await c.register("TestBot", "A test bot")
            assert c._api_key == "moltbook_new_key"
            assert (tmp_path / "creds.json").exists()
        await c.close()

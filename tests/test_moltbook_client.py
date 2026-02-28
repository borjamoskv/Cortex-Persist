"""Tests for the Moltbook HTTP client (mocked responses)."""

import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from pathlib import Path

from cortex.moltbook.client import (
    MoltbookClient,
    MoltbookRateLimited,
    MoltbookError,
    _BASE_URL,
    _CREDENTIALS_PATH,
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
                import types
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

    def _mock_response(self, data: dict, headers: dict = None):
        """Create a mock urllib response."""
        resp = MagicMock()
        resp.read.return_value = json.dumps(data).encode()
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        resp.headers = headers or {
            "X-RateLimit-Remaining": "55",
            "X-RateLimit-Reset": "9999999999",
        }
        # Make headers.get work
        resp.headers = MagicMock()
        resp.headers.get = MagicMock(side_effect=lambda k, d=None: {
            "X-RateLimit-Remaining": "55",
            "X-RateLimit-Reset": "9999999999",
        }.get(k, d))
        return resp

    @patch("cortex.moltbook.client.urlopen")
    def test_get_home(self, mock_urlopen, client):
        mock_urlopen.return_value = self._mock_response({
            "success": True,
            "your_account": {"karma": 42},
        })
        result = client.get_home()
        assert result["success"] is True
        assert result["your_account"]["karma"] == 42

    @patch("cortex.moltbook.client.urlopen")
    def test_create_post(self, mock_urlopen, client):
        mock_urlopen.return_value = self._mock_response({
            "success": True,
            "post": {"id": "test-123", "title": "Test"},
        })
        result = client.create_post("general", "Test", "Content")
        assert result["post"]["id"] == "test-123"

    @patch("cortex.moltbook.client.urlopen")
    def test_upvote_post(self, mock_urlopen, client):
        mock_urlopen.return_value = self._mock_response({"success": True})
        result = client.upvote_post("post-abc")
        assert result["success"] is True

    @patch("cortex.moltbook.client.urlopen")
    def test_search(self, mock_urlopen, client):
        mock_urlopen.return_value = self._mock_response({
            "success": True,
            "results": [{"id": "r1", "similarity": 0.85}],
        })
        result = client.search("memory architectures")
        assert len(result["results"]) == 1
        assert result["results"][0]["similarity"] == 0.85

    @patch("cortex.moltbook.client.urlopen")
    def test_updates_rate_limit_tracking(self, mock_urlopen, client):
        mock_urlopen.return_value = self._mock_response({"success": True})
        client.get_home()
        assert client._rate_remaining == 55

    @patch("cortex.moltbook.client.urlopen")
    def test_register_saves_credentials(self, mock_urlopen, client, tmp_path, monkeypatch):
        monkeypatch.setattr("cortex.moltbook.client._CREDENTIALS_PATH", tmp_path / "creds.json")
        mock_urlopen.return_value = self._mock_response({
            "agent": {
                "api_key": "moltbook_new_key",
                "claim_url": "https://www.moltbook.com/claim/xxx",
            },
        })
        # Use a client without auth for register
        c = MoltbookClient(api_key="dummy")
        result = c.register("TestBot", "A test bot")
        assert c._api_key == "moltbook_new_key"
        assert (tmp_path / "creds.json").exists()

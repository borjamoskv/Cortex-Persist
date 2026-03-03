"""Tests for MoltbookAuth helper — Zero-Trust compliance (Ω₃)."""
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from scripts.moltbook_auth import (
    MoltbookAuth, MoltbookAuthError, MoltbookTokenExpired, VerifiedAgent
)


# --- Initialization ---

def test_init_with_explicit_key():
    auth = MoltbookAuth(app_key="test_key")
    assert auth.app_key == "test_key"


def test_init_from_env(monkeypatch):
    monkeypatch.setenv("MOLTBOOK_APP_KEY", "env_key")
    auth = MoltbookAuth()
    assert auth.app_key == "env_key"


def test_init_missing_config(monkeypatch):
    monkeypatch.delenv("MOLTBOOK_APP_KEY", raising=False)
    with pytest.raises(MoltbookAuthError, match="MOLTBOOK_APP_KEY not found"):
        MoltbookAuth()


# --- verify_request ---

@pytest.mark.asyncio
async def test_verify_missing_header():
    auth = MoltbookAuth(app_key="k")
    with pytest.raises(MoltbookAuthError, match="Missing X-Moltbook-Identity"):
        await auth.verify_request({})


@pytest.mark.asyncio
async def test_verify_success():
    auth = MoltbookAuth(app_key="k")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "valid": True,
        "agent": {
            "id": "a1", "name": "TestBot", "description": "d",
            "karma": 42, "is_claimed": True, "follower_count": 7,
            "stats": {"posts": 3}, "owner": {"id": "u1"}
        }
    }

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("scripts.moltbook_auth.httpx.AsyncClient", return_value=mock_client):
        agent = await auth.verify_request({"X-Moltbook-Identity": "tok"})

    assert isinstance(agent, VerifiedAgent)
    assert agent.id == "a1"
    assert agent.karma == 42
    assert agent.is_claimed is True


@pytest.mark.asyncio
async def test_verify_expired_token():
    auth = MoltbookAuth(app_key="k")
    mock_resp = MagicMock()
    mock_resp.status_code = 401

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("scripts.moltbook_auth.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(MoltbookTokenExpired):
            await auth.verify_request({"X-Moltbook-Identity": "expired"})


@pytest.mark.asyncio
async def test_verify_invalid_payload():
    auth = MoltbookAuth(app_key="k")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"valid": False, "message": "Signature mismatch"}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("scripts.moltbook_auth.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(MoltbookAuthError, match="Signature mismatch"):
            await auth.verify_request({"X-Moltbook-Identity": "bad"})


@pytest.mark.asyncio
async def test_verify_server_error():
    auth = MoltbookAuth(app_key="k")
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("scripts.moltbook_auth.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(MoltbookAuthError, match="status 500"):
            await auth.verify_request({"X-Moltbook-Identity": "t"})

"""Tests for cortex.gateway.jules — Jules API Client."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.gateway.jules import (
    JULES_API_BASE,
    JulesAPIError,
    JulesClient,
    source_from_repo,
)


class TestSourceFromRepo:
    def test_standard(self) -> None:
        assert source_from_repo("borjamoskv", "Cortex-Persist") == (
            "sources/github/borjamoskv/Cortex-Persist"
        )

    def test_org_repo(self) -> None:
        assert source_from_repo("google", "jules") == "sources/github/google/jules"


class TestJulesAPIError:
    def test_repr(self) -> None:
        err = JulesAPIError(403, "forbidden", "POST", "/sessions")
        assert "403" in str(err)
        assert "forbidden" in str(err)

    def test_attributes(self) -> None:
        err = JulesAPIError(500, "internal", "GET", "/sessions/123")
        assert err.status == 500
        assert err.method == "GET"


class TestJulesClientInit:
    def test_missing_key_raises(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="API key required"):
                JulesClient(api_key="")

    def test_env_key(self) -> None:
        with patch.dict("os.environ", {"JULES_API_KEY": "test-key-123"}):
            client = JulesClient()
            assert client._api_key == "test-key-123"

    def test_explicit_key(self) -> None:
        client = JulesClient(api_key="explicit-key")
        assert client._api_key == "explicit-key"


class TestJulesClientMethods:
    """Test client methods with mocked HTTP."""

    @pytest.fixture
    def client(self) -> JulesClient:
        return JulesClient(api_key="test-key")

    @pytest.fixture
    def mock_request(self, client: JulesClient) -> AsyncMock:
        mock = AsyncMock()
        client._request = mock  # type: ignore[assignment]
        return mock

    @pytest.mark.asyncio
    async def test_create_session(
        self, client: JulesClient, mock_request: AsyncMock
    ) -> None:
        mock_request.return_value = {
            "name": "sessions/12345",
            "state": "ACTIVE",
        }

        result = await client.create_session(
            prompt="Fix the test",
            source="sources/github/borjamoskv/Cortex-Persist",
            branch="main",
            title="Test Fix",
        )

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/sessions"
        body = call_args[1]["json_body"]
        assert body["prompt"] == "Fix the test"
        assert body["title"] == "Test Fix"
        assert body["sourceContext"]["source"] == "sources/github/borjamoskv/Cortex-Persist"
        assert result["name"] == "sessions/12345"

    @pytest.mark.asyncio
    async def test_list_sessions(
        self, client: JulesClient, mock_request: AsyncMock
    ) -> None:
        mock_request.return_value = {"sessions": [{"name": "sessions/1"}]}

        result = await client.list_sessions(page_size=5)

        mock_request.assert_called_once_with(
            "GET", "/sessions", params={"pageSize": "5"}
        )
        assert len(result["sessions"]) == 1

    @pytest.mark.asyncio
    async def test_get_session(
        self, client: JulesClient, mock_request: AsyncMock
    ) -> None:
        mock_request.return_value = {"name": "sessions/99", "state": "COMPLETED"}

        result = await client.get_session("99")

        mock_request.assert_called_once_with("GET", "/sessions/99")
        assert result["state"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_send_message(
        self, client: JulesClient, mock_request: AsyncMock
    ) -> None:
        mock_request.return_value = {}

        await client.send_message("99", "do more work")

        mock_request.assert_called_once_with(
            "POST",
            "/sessions/99:sendMessage",
            json_body={"message": "do more work"},
        )

    @pytest.mark.asyncio
    async def test_approve_plan(
        self, client: JulesClient, mock_request: AsyncMock
    ) -> None:
        mock_request.return_value = {}

        await client.approve_plan("99")

        mock_request.assert_called_once_with(
            "POST", "/sessions/99:approvePlan", json_body={}
        )

    @pytest.mark.asyncio
    async def test_list_activities(
        self, client: JulesClient, mock_request: AsyncMock
    ) -> None:
        mock_request.return_value = {"activities": [{"type": "plan"}]}

        result = await client.list_activities("99", page_size=10)

        mock_request.assert_called_once_with(
            "GET",
            "/sessions/99/activities",
            params={"pageSize": "10"},
        )
        assert len(result["activities"]) == 1

    @pytest.mark.asyncio
    async def test_list_sources(
        self, client: JulesClient, mock_request: AsyncMock
    ) -> None:
        mock_request.return_value = {"sources": []}

        await client.list_sources()

        mock_request.assert_called_once_with("GET", "/sources")

from __future__ import annotations

import pytest

from cortex.api.async_client import AsyncCortexClient
from cortex.api.client import CortexClient


def test_sync_client_recall_forwards_include_deprecated_flag() -> None:
    client = CortexClient("http://example.test")

    captured: dict[str, object] = {}

    def fake_request(method: str, path: str, **kwargs: object) -> list[dict[str, object]]:
        captured["method"] = method
        captured["path"] = path
        captured["params"] = kwargs.get("params")
        return []

    client._request = fake_request  # type: ignore[method-assign]

    result = client.recall("alpha", include_deprecated=True)

    assert result == []
    assert captured == {
        "method": "GET",
        "path": "/v1/projects/alpha/facts",
        "params": {"include_deprecated": "true"},
    }

    client.close()


@pytest.mark.asyncio
async def test_async_client_recall_forwards_include_deprecated_flag() -> None:
    client = AsyncCortexClient("http://example.test")

    captured: dict[str, object] = {}

    async def fake_request(method: str, path: str, **kwargs: object) -> list[dict[str, object]]:
        captured["method"] = method
        captured["path"] = path
        captured["params"] = kwargs.get("params")
        return []

    client._request = fake_request  # type: ignore[method-assign]

    result = await client.recall("alpha", include_deprecated=True, limit=20, offset=5)

    assert result == []
    assert captured == {
        "method": "GET",
        "path": "/v1/projects/alpha/facts",
        "params": {
            "limit": 20,
            "offset": 5,
            "include_deprecated": "true",
        },
    }

    await client.close()

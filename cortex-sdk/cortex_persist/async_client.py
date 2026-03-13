"""cortex-persist — Async Client.

Usage:
    from cortex_persist import AsyncCortexMemory

    async with AsyncCortexMemory(api_key="ctx_...") as memory:
        await memory.store("my-agent", "User prefers dark mode")
        results = await memory.search("what does the user prefer?")
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

import httpx

from cortex_persist.exceptions import CortexError
from cortex_persist.models import Memory

__all__ = ["AsyncCortexMemory"]


class AsyncCortexMemory:
    """Async Python SDK for the CORTEX Persistence API.

    Args:
        api_key: Your CORTEX API key (starts with ctx_).
        base_url: API server URL. Defaults to https://cortex.moskv.com.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://cortex.moskv.com",
        timeout: float = 30.0,
    ):
        self.api_key = api_key or os.environ.get("CORTEX_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._headers(),
        )
        self._semaphore = asyncio.Semaphore(100)

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        max_retries = 3
        backoff = 0.5

        for attempt in range(max_retries):
            try:
                async with self._semaphore:
                    resp = await self._client.request(method, path, **kwargs)

                if resp.status_code >= 500 and attempt < max_retries - 1:
                    await asyncio.sleep(backoff * (2 ** attempt))
                    continue

                if resp.status_code >= 400:
                    try:
                        detail = resp.json().get("detail", resp.text)
                    except (ValueError, KeyError):
                        detail = resp.text
                    raise CortexError(resp.status_code, detail)

                return resp.json()

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff * (2 ** attempt))
                    continue
                raise CortexError(0, f"Connection error: {e}") from e

    # ─── Core Operations ─────────────────────────────────────────────

    async def store(
        self,
        project: str,
        content: str,
        type: str = "knowledge",
        tags: Optional[list[str]] = None,
        source: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> int:
        """Store a memory. Returns the memory ID."""
        data: dict[str, Any] = {
            "project": project,
            "content": content,
            "type": type,
            "tags": tags or [],
        }
        if source:
            data["source"] = source
        if metadata:
            data["metadata"] = metadata
        result = await self._request("POST", "/v1/memories", json=data)
        return result["id"]

    async def search(
        self,
        query: str,
        k: int = 5,
        project: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> list[Memory]:
        """Semantic search. Returns ranked memories."""
        data: dict[str, Any] = {"query": query, "k": k}
        if project:
            data["project"] = project
        if tags:
            data["tags"] = tags
        results = await self._request("POST", "/v1/memories/search", json=data)
        return [Memory.from_dict(r) for r in results]

    async def list(
        self,
        project: str,
        limit: int = 50,
    ) -> list[Memory]:
        """List all memories for a project."""
        results = await self._request(
            "GET", "/v1/memories", params={"project": project, "limit": limit}
        )
        return [Memory.from_dict(r) for r in results]

    async def get(self, memory_id: int) -> Memory:
        """Get a single memory by ID."""
        result = await self._request("GET", f"/v1/memories/{memory_id}")
        return Memory.from_dict(result)

    async def delete(self, memory_id: int) -> bool:
        """Delete a memory."""
        await self._request("DELETE", f"/v1/memories/{memory_id}")
        return True

    async def batch_store(self, memories: list[dict[str, Any]]) -> dict:
        """Batch store up to 100 memories."""
        return await self._request(
            "POST", "/v1/memories/batch", json={"memories": memories}
        )

    async def verify(self) -> dict:
        """Verify ledger integrity."""
        return await self._request("GET", "/v1/memories/verify")

    async def usage(self) -> dict:
        """Get current API usage."""
        return await self._request("GET", "/v1/usage")

    # ─── Context Manager ─────────────────────────────────────────────

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncCortexMemory:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

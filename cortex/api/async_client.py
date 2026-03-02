"""
CORTEX v5.0 — Async Python SDK Client.

Fully asynchronous client for the CORTEX REST API using httpx.AsyncClient.

Usage:
    from cortex.async_client import AsyncCortexClient

    async with AsyncCortexClient("http://localhost:8484", api_key="ctx_...") as client:
        await client.store("my-project", "Important fact")
        results = await client.search("what is important?")
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx

from cortex.api.client import CortexError, Fact
from cortex.immune.chaos import ChaosGate, async_interceptor

__all__ = ["AsyncCortexClient"]


class AsyncCortexClient:
    """Async Python SDK for the CORTEX Sovereign Memory API.

    Args:
        base_url: API server URL (default: http://localhost:8484)
        api_key: API key (or set CORTEX_API_KEY env var)
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8484",
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("CORTEX_API_KEY", "")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._headers(),
        )
        # Límite estricto para escalar a 1k rpm sin timeout
        self._semaphore = asyncio.Semaphore(100)
        self.chaos_gate = ChaosGate(name=f"api_client:{self.base_url}")

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        # Chronos Sniper Guard: Exponential Backoff Retries
        max_retries = 3
        backoff = 0.5

        for attempt in range(max_retries):
            try:
                async with self._semaphore:
                    # Chaos Interceptor Logic-Bomb
                    resp = await async_interceptor(
                        self.chaos_gate,
                        self._client.request,
                        method,
                        path,
                        **kwargs,
                    )

                if resp.status_code >= 500:
                    # Server error, maybe retry
                    if attempt < max_retries - 1:
                        await asyncio.sleep(backoff * (2**attempt))
                        continue

                if resp.status_code >= 400:
                    try:
                        detail = resp.json().get("detail", resp.text)
                    except (ValueError, KeyError):
                        detail = resp.text
                    raise CortexError(resp.status_code, detail)

                try:
                    return resp.json()
                except ValueError as e:
                    raise CortexError(resp.status_code, f"Invalid JSON response: {e}") from e

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff * (2**attempt))
                    continue
                raise CortexError(0, f"Connection error after {max_retries} attempts: {e}") from e
            except httpx.HTTPError as e:
                raise CortexError(0, f"HTTP error: {e}") from e

    # ─── Facts ────────────────────────────────────────────────────────

    async def store(
        self,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Store a fact. Returns fact ID."""
        data = {
            "project": project,
            "content": content,
            "fact_type": fact_type,
            "tags": tags or [],
        }
        if metadata:
            data["metadata"] = metadata
        result = await self._request("POST", "/v1/facts", json=data)
        return result["fact_id"]

    async def store_many(
        self,
        facts: list[dict[str, Any]],
    ) -> list[int]:
        """Batch store facts. Returns list of fact IDs."""
        result = await self._request("POST", "/v1/facts/batch", json={"facts": facts})
        return result["fact_ids"]

    async def search(
        self,
        query: str,
        k: int = 5,
        project: str | None = None,
        tags: list[str] | None = None,
        fact_type: str | None = None,
    ) -> list[Fact]:
        """Semantic search. Returns ranked facts."""
        data: dict[str, Any] = {"query": query, "k": k}
        if project:
            data["project"] = project
        if tags:
            data["tags"] = tags
        if fact_type:
            data["fact_type"] = fact_type
        results = await self._request("POST", "/v1/search", json=data)
        return [
            Fact(
                id=r["fact_id"],
                project=r["project"],
                content=r["content"],
                fact_type=r["fact_type"],
                tags=r.get("tags", []),
                created_at="",
                valid_from="",
                score=r.get("score", 0.0),
            )
            for r in results
        ]

    async def recall(
        self,
        project: str,
        include_deprecated: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Fact]:
        """Get facts for a project with optional pagination."""
        params: dict[str, Any] = {
            "include_deprecated": str(include_deprecated).lower(),
        }
        if limit is not None:
            params["limit"] = limit
            params["offset"] = offset
        results = await self._request(
            "GET",
            f"/v1/projects/{project}/facts",
            params=params,
        )
        return [
            Fact(
                id=f["id"],
                project=f["project"],
                content=f["content"],
                fact_type=f["fact_type"],
                tags=f.get("tags", []),
                created_at=f.get("created_at", ""),
                valid_from=f.get("valid_from", ""),
                valid_until=f.get("valid_until"),
            )
            for f in results
        ]

    async def deprecate(self, fact_id: int) -> bool:
        """Deprecate a fact (soft delete)."""
        await self._request("DELETE", f"/v1/facts/{fact_id}")
        return True

    async def update(
        self,
        fact_id: int,
        content: str | None = None,
        tags: list[str] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> int:
        """Update a fact. Returns new fact ID."""
        data: dict[str, Any] = {}
        if content is not None:
            data["content"] = content
        if tags is not None:
            data["tags"] = tags
        if meta is not None:
            data["meta"] = meta
        result = await self._request("PATCH", f"/v1/facts/{fact_id}", json=data)
        return result["fact_id"]

    async def export(
        self,
        project: str,
        fmt: str = "json",
    ) -> dict[str, Any]:
        """Export project facts in specified format (json, csv, jsonl)."""
        result = await self._request(
            "GET",
            f"/v1/projects/{project}/export",
            params={"format": fmt},
        )
        return result

    async def status(self) -> dict[str, Any]:
        """Get engine status."""
        return await self._request("GET", "/v1/status")

    # ─── Admin ────────────────────────────────────────────────────────

    async def create_key(self, name: str, tenant_id: str = "default") -> dict[str, Any]:
        """Create a new API key (admin only)."""
        return await self._request(
            "POST",
            "/v1/admin/keys",
            params={"name": name, "tenant_id": tenant_id},
        )

    async def list_keys(self) -> list[dict[str, Any]]:
        """List all API keys (admin only)."""
        return await self._request("GET", "/v1/admin/keys")  # type: ignore[reportReturnType]

    # ─── Context Manager ──────────────────────────────────────────────

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self) -> AsyncCortexClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

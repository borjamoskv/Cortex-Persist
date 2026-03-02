"""cortex-memory — Synchronous Client.

Usage:
    from cortex_memory import CortexMemory

    memory = CortexMemory(api_key="ctx_...")
    memory.store("my-agent", "User prefers dark mode")
    results = memory.search("what does the user prefer?")
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx

from cortex_memory.exceptions import CortexError
from cortex_memory.models import Memory

__all__ = ["CortexMemory"]


class CortexMemory:
    """Synchronous Python SDK for the CORTEX Memory API.

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
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._headers(),
        )

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        resp = self._client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except (ValueError, KeyError):
                detail = resp.text
            raise CortexError(resp.status_code, detail)
        return resp.json()

    # ─── Core Operations ─────────────────────────────────────────────

    def store(
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
        result = self._request("POST", "/v1/memories", json=data)
        return result["id"]

    def search(
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
        results = self._request("POST", "/v1/memories/search", json=data)
        return [Memory.from_dict(r) for r in results]

    def list(
        self,
        project: str,
        limit: int = 50,
    ) -> list[Memory]:
        """List all memories for a project."""
        results = self._request(
            "GET", "/v1/memories", params={"project": project, "limit": limit}
        )
        return [Memory.from_dict(r) for r in results]

    def get(self, memory_id: int) -> Memory:
        """Get a single memory by ID."""
        result = self._request("GET", f"/v1/memories/{memory_id}")
        return Memory.from_dict(result)

    def delete(self, memory_id: int) -> bool:
        """Delete a memory."""
        self._request("DELETE", f"/v1/memories/{memory_id}")
        return True

    def batch_store(self, memories: list[dict[str, Any]]) -> dict:
        """Batch store up to 100 memories."""
        return self._request(
            "POST", "/v1/memories/batch", json={"memories": memories}
        )

    def verify(self) -> dict:
        """Verify ledger integrity."""
        return self._request("GET", "/v1/memories/verify")

    def usage(self) -> dict:
        """Get current API usage."""
        return self._request("GET", "/v1/usage")

    # ─── Context Manager ─────────────────────────────────────────────

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> CortexMemory:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

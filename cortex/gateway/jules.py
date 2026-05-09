"""CORTEX Gateway — Jules API Client.

Direct HTTP transport to jules.googleapis.com/v1alpha.
Handles session lifecycle: create, list, get, sendMessage, approvePlan, activities.

Authentication: X-Goog-Api-Key header.
Retry: exponential backoff (3 attempts, 1s base).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger("cortex.gateway.jules")

JULES_API_BASE = "https://jules.googleapis.com/v1alpha"
JULES_API_KEY_ENV = "JULES_API_KEY"

# Retry config
MAX_RETRIES = 3
BACKOFF_BASE_S = 1.0


class JulesAPIError(Exception):
    """Raised when Jules API returns a non-2xx response."""

    def __init__(self, status: int, body: str, method: str, url: str) -> None:
        self.status = status
        self.body = body
        self.method = method
        self.url = url
        super().__init__(f"Jules API {method} {url} → {status}: {body[:200]}")


class JulesClient:
    """Async HTTP client for Jules API v1alpha.

    Usage:
        async with JulesClient(api_key="...") as client:
            session = await client.create_session(
                prompt="Fix the broken test",
                source="sources/github/borjamoskv/Cortex-Persist",
                branch="main",
            )
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get(JULES_API_KEY_ENV, "")
        if not self._api_key:
            raise ValueError(
                f"Jules API key required. Set {JULES_API_KEY_ENV} env var "
                "or pass api_key= to JulesClient."
            )
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> JulesClient:
        self._session = aiohttp.ClientSession(
            headers={
                "X-Goog-Api-Key": self._api_key,
                "Content-Type": "application/json",
            },
            timeout=aiohttp.ClientTimeout(total=120),
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    # ── Internal HTTP ─────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute HTTP request with exponential backoff retry."""
        if not self._session:
            raise RuntimeError("JulesClient not initialized. Use 'async with'.")

        url = f"{JULES_API_BASE}{path}"
        last_err: JulesAPIError | None = None

        for attempt in range(MAX_RETRIES):
            try:
                async with self._session.request(
                    method, url, json=json_body, params=params
                ) as resp:
                    body = await resp.text()
                    if resp.status >= 400:
                        raise JulesAPIError(resp.status, body, method, url)
                    if not body.strip():
                        return {}
                    return await resp.json()
            except JulesAPIError as e:
                last_err = e
                # Don't retry client errors (4xx) except 429
                if 400 <= e.status < 500 and e.status != 429:
                    raise
                wait = BACKOFF_BASE_S * (2**attempt)
                logger.warning(
                    "Jules API retry %d/%d after %.1fs: %s",
                    attempt + 1, MAX_RETRIES, wait, e,
                )
                await asyncio.sleep(wait)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                wait = BACKOFF_BASE_S * (2**attempt)
                logger.warning(
                    "Jules API network retry %d/%d after %.1fs: %s",
                    attempt + 1, MAX_RETRIES, wait, e,
                )
                last_err = JulesAPIError(0, str(e), method, url)
                await asyncio.sleep(wait)

        raise last_err or RuntimeError("Jules API: max retries exhausted")

    # ── Sessions ──────────────────────────────────────────────

    async def create_session(
        self,
        prompt: str,
        source: str,
        *,
        branch: str = "main",
        title: str | None = None,
        require_plan_approval: bool = True,
    ) -> dict[str, Any]:
        """Create a new Jules session.

        Args:
            prompt: Task description for Jules.
            source: Source identifier (e.g. "sources/github/owner/repo").
            branch: Starting branch name.
            title: Optional human-readable title.
            require_plan_approval: If True, Jules pauses for plan approval.

        Returns:
            Session object from API.
        """
        body: dict[str, Any] = {
            "prompt": prompt,
            "sourceContext": {
                "source": source,
                "githubRepoContext": {"startingBranch": branch},
            },
            "requirePlanApproval": require_plan_approval,
        }
        if title:
            body["title"] = title

        result = await self._request("POST", "/sessions", json_body=body)
        session_name = result.get("name", "unknown")
        logger.info("Jules session created: %s", session_name)
        return result

    async def list_sessions(
        self, *, page_size: int = 30, page_token: str | None = None
    ) -> dict[str, Any]:
        """List Jules sessions."""
        params: dict[str, str] = {"pageSize": str(page_size)}
        if page_token:
            params["pageToken"] = page_token
        return await self._request("GET", "/sessions", params=params)

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """Get a specific session by ID."""
        return await self._request("GET", f"/sessions/{session_id}")

    async def send_message(self, session_id: str, message: str) -> dict[str, Any]:
        """Send a message to an active Jules session."""
        return await self._request(
            "POST",
            f"/sessions/{session_id}:sendMessage",
            json_body={"message": message},
        )

    async def approve_plan(self, session_id: str) -> dict[str, Any]:
        """Approve a pending plan in a Jules session."""
        return await self._request(
            "POST", f"/sessions/{session_id}:approvePlan", json_body={}
        )

    # ── Activities ────────────────────────────────────────────

    async def list_activities(
        self, session_id: str, *, page_size: int = 50
    ) -> dict[str, Any]:
        """List activities (steps) within a session."""
        return await self._request(
            "GET",
            f"/sessions/{session_id}/activities",
            params={"pageSize": str(page_size)},
        )

    # ── Sources ───────────────────────────────────────────────

    async def list_sources(self) -> dict[str, Any]:
        """List available sources (connected repos)."""
        return await self._request("GET", "/sources")

    # ── Convenience ───────────────────────────────────────────

    async def wait_for_completion(
        self,
        session_id: str,
        *,
        poll_interval_s: float = 10.0,
        timeout_s: float = 600.0,
    ) -> dict[str, Any]:
        """Poll a session until it completes or times out.

        Returns:
            Final session state.
        """
        import time

        deadline = time.monotonic() + timeout_s
        terminal_states = {"COMPLETED", "FAILED", "CANCELLED"}

        while time.monotonic() < deadline:
            session = await self.get_session(session_id)
            state = session.get("state", "UNKNOWN")
            logger.debug("Jules session %s state: %s", session_id, state)

            if state in terminal_states:
                logger.info(
                    "Jules session %s reached terminal state: %s",
                    session_id, state,
                )
                return session

            await asyncio.sleep(poll_interval_s)

        raise TimeoutError(
            f"Jules session {session_id} did not complete within {timeout_s}s"
        )


def source_from_repo(owner: str, repo: str) -> str:
    """Build Jules source identifier from GitHub owner/repo."""
    return f"sources/github/{owner}/{repo}"

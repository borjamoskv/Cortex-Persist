"""Moltbook HTTP client — rate-limit aware, zero-trust.

All requests go exclusively to https://www.moltbook.com/api/v1/*.
API key is never sent anywhere else.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.moltbook.com/api/v1"
_CREDENTIALS_PATH = Path.home() / ".config" / "moltbook" / "credentials.json"
_TIMEOUT = 30.0


class MoltbookRateLimited(Exception):
    """Raised when rate limit is hit."""

    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after}s")


class MoltbookError(Exception):
    """Generic Moltbook API error."""

    def __init__(self, status: int, message: str, hint: str = ""):
        self.status = status
        self.hint = hint
        super().__init__(f"[{status}] {message}" + (f" (hint: {hint})" if hint else ""))


class MoltbookClient:
    """Async HTTP client for Moltbook API.
    Zero-trust: auth header is ONLY sent to www.moltbook.com.
    Rate-limit aware: reads X-RateLimit-* headers, respects Retry-After.
    """

    def __init__(self, api_key: str | None = None, proxy: str | None = None):
        self._api_key = api_key or self._try_load_api_key()
        self._rate_remaining: int = 60
        self._rate_reset: float = 0.0
        self._client = httpx.AsyncClient(timeout=_TIMEOUT, proxy=proxy)

        # State mapping for pre-flight etc
        self._suspended_until = 0.0
        self._suspended_reason = ""

    def _try_load_api_key(self) -> str | None:
        """Attempt to load API key, return None if not found."""
        env_key = os.environ.get("MOLTBOOK_API_KEY")
        if env_key:
            return env_key

        if _CREDENTIALS_PATH.exists():
            try:
                data = json.loads(_CREDENTIALS_PATH.read_text())
                return data.get("api_key")
            except (OSError, json.JSONDecodeError):
                return None
        return None

    @staticmethod
    def save_credentials(api_key: str, agent_name: str) -> Path:
        """Persist credentials to disk."""
        _CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        creds = {"api_key": api_key, "agent_name": agent_name}
        _CREDENTIALS_PATH.write_text(json.dumps(creds, indent=2))
        _CREDENTIALS_PATH.chmod(0o600)  # Owner-only read/write
        logger.info("Credentials saved to %s", _CREDENTIALS_PATH)
        return _CREDENTIALS_PATH

    async def _request(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        auth: bool = True,
    ) -> dict[str, Any]:
        """Make an async HTTP request to the Moltbook API."""
        url = f"{_BASE_URL}{path}"

        if not url.startswith("https://www.moltbook.com/"):
            raise ValueError(f"SECURITY: refusing to send request to {url}")

        if self._rate_remaining <= 0 and time.time() < self._rate_reset:
            wait = int(self._rate_reset - time.time()) + 1
            raise MoltbookRateLimited(retry_after=wait)

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if auth and self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            if method.upper() == "GET":
                resp = await self._client.request(method, url, params=data, headers=headers)
            else:
                resp = await self._client.request(method, url, json=data, headers=headers)

            # Update rate limit tracking
            remaining = resp.headers.get("X-RateLimit-Remaining")
            if remaining is not None:
                self._rate_remaining = int(remaining)
            reset = resp.headers.get("X-RateLimit-Reset")
            if reset is not None:
                self._rate_reset = float(reset)

            if resp.status_code == 429:
                retry = int(resp.headers.get("Retry-After", "60"))
                raise MoltbookRateLimited(retry_after=retry)

            if resp.status_code >= 400:
                is_json = resp.headers.get("Content-Type") == "application/json"
                err_data = resp.json() if is_json else {}
                raise MoltbookError(
                    status=resp.status_code,
                    message=err_data.get("error", resp.text),
                    hint=err_data.get("hint", ""),
                )

            return resp.json()

        except httpx.HTTPError as e:
            logger.error("Moltbook API error: %s", e)
            raise

    # ─── Registration ──────────────────────────────────────────

    async def register(self, name: str, description: str = "") -> dict[str, Any]:
        """Register a new agent. No auth required."""
        result = await self._request(
            "POST",
            "/agents/register",
            data={"name": name, "description": description or f"CORTEX Dynamic Agent: {name}"},
            auth=False,
        )
        agent = result.get("agent", {})
        api_key = agent.get("api_key", "")
        if api_key:
            self._api_key = api_key
            self.save_credentials(api_key, name)
        return result

    async def ensure_identity(self, name: str):
        """Register if no API key is found."""
        if not self._api_key:
            logger.info(
                "No identity found for '%s'. Registering automatically in MOLTBOOK...", name
            )
            await self.register(name)

    async def check_status(self) -> dict[str, Any]:
        """Check claim status."""
        return await self._request("GET", "/agents/status")

    # ─── Home / Dashboard ──────────────────────────────────────

    async def get_home(self) -> dict[str, Any]:
        """Get the /home dashboard — single call for everything."""
        return await self._request("GET", "/home")

    # ─── Posts ─────────────────────────────────────────────────

    async def create_post(
        self,
        submolt_name: str,
        title: str,
        content: str = "",
        post_type: str = "text",
        url: str = "",
    ) -> dict[str, Any]:
        """Create a post in a submolt."""
        payload: dict[str, str] = {
            "submolt_name": submolt_name,
            "title": title,
            "type": post_type,
        }
        if content:
            payload["content"] = content
        if url:
            payload["url"] = url
        return await self._request("POST", "/posts", data=payload)

    async def get_feed(
        self, sort: str = "hot", limit: int = 25, cursor: str = ""
    ) -> dict[str, Any]:
        """Get the main feed."""
        params = f"?sort={sort}&limit={limit}"
        if cursor:
            params += f"&cursor={cursor}"
        return await self._request("GET", f"/posts{params}")

    async def get_post(self, post_id: str) -> dict[str, Any]:
        """Get a single post by ID."""
        return await self._request("GET", f"/posts/{post_id}")

    async def delete_post(self, post_id: str) -> dict[str, Any]:
        """Delete your post."""
        return await self._request("DELETE", f"/posts/{post_id}")

    # ─── Comments ──────────────────────────────────────────────

    async def create_comment(
        self, post_id: str, content: str, parent_id: str = ""
    ) -> dict[str, Any]:
        """Add a comment (or reply) to a post."""
        payload: dict[str, str] = {"content": content}
        if parent_id:
            payload["parent_id"] = parent_id
        return await self._request("POST", f"/posts/{post_id}/comments", data=payload)

    async def get_comments(self, post_id: str, sort: str = "best") -> dict[str, Any]:
        """Get comments on a post."""
        return await self._request("GET", f"/posts/{post_id}/comments?sort={sort}")

    # ─── Voting ────────────────────────────────────────────────

    async def upvote_post(self, post_id: str) -> dict[str, Any]:
        """Upvote a post."""
        return await self._request("POST", f"/posts/{post_id}/upvote")

    async def downvote_post(self, post_id: str) -> dict[str, Any]:
        """Downvote a post."""
        return await self._request("POST", f"/posts/{post_id}/downvote")

    async def upvote_comment(self, comment_id: str) -> dict[str, Any]:
        """Upvote a comment."""
        return await self._request("POST", f"/comments/{comment_id}/upvote")

    # ─── Search ────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        search_type: str = "all",
        limit: int = 20,
        cursor: str = "",
    ) -> dict[str, Any]:
        """Semantic search across posts and comments."""
        params = {"q": query, "type": search_type, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        # Note: data for GET might need params handling
        return await self._request("GET", "/search", data=params)

    # ─── Verification ──────────────────────────────────────────

    async def submit_verification(self, verification_code: str, answer: str) -> dict[str, Any]:
        """Submit answer to a verification challenge."""
        return await self._request(
            "POST",
            "/verify",
            data={"verification_code": verification_code, "answer": answer},
        )

    # ─── Profile ───────────────────────────────────────────────

    async def get_me(self) -> dict[str, Any]:
        """Get your agent profile."""
        return await self._request("GET", "/agents/me")

    async def get_profile(self, agent_name: str) -> dict[str, Any]:
        """Get another agent's profile."""
        return await self._request("GET", f"/agents/profile/{agent_name}")

    async def update_profile(self, **fields: str) -> dict[str, Any]:
        """Update profile fields (bio, website, etc)."""
        return await self._request("PATCH", "/agents/me", data=fields)

    # ─── Following ─────────────────────────────────────────────

    async def follow(self, agent_name: str) -> dict[str, Any]:
        """Follow another molty."""
        return await self._request("POST", f"/agents/{agent_name}/follow")

    async def unfollow(self, agent_name: str) -> dict[str, Any]:
        """Unfollow a molty."""
        return await self._request("DELETE", f"/agents/{agent_name}/follow")

    # ─── Submolts ──────────────────────────────────────────────

    async def list_submolts(self) -> dict[str, Any]:
        """List all submolts."""
        return await self._request("GET", "/submolts")

    async def subscribe(self, submolt_name: str) -> dict[str, Any]:
        """Subscribe to a submolt."""
        return await self._request("POST", f"/submolts/{submolt_name}/subscribe")

    # ─── DMs ───────────────────────────────────────────────────

    async def get_dm_requests(self) -> dict[str, Any]:
        """Get pending DM requests."""
        return await self._request("GET", "/agents/dm/requests")

    async def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        """Read a DM conversation."""
        return await self._request("GET", f"/agents/dm/conversations/{conversation_id}")

    async def send_dm(self, conversation_id: str, message: str) -> dict[str, Any]:
        """Reply to a DM conversation."""
        return await self._request(
            "POST",
            f"/agents/dm/conversations/{conversation_id}/send",
            data={"message": message},
        )

    # ─── Notifications ─────────────────────────────────────────

    async def mark_notifications_read(self, post_id: str) -> dict[str, Any]:
        """Mark notifications for a post as read."""
        return await self._request("POST", f"/notifications/read-by-post/{post_id}")

    async def close(self):
        """Close the httpx client."""
        await self._client.aclose()

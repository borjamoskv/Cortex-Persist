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
from typing import Any, Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen



logger = logging.getLogger(__name__)

_BASE_URL = "https://www.moltbook.com/api/v1"
_CREDENTIALS_PATH = Path.home() / ".config" / "moltbook" / "credentials.json"
_TIMEOUT = 30


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
    """HTTP client for Moltbook API.

    Zero-trust: auth header is ONLY sent to www.moltbook.com.
    Rate-limit aware: reads X-RateLimit-* headers, respects Retry-After.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or self._load_api_key()
        self._rate_remaining: int = 60
        self._rate_reset: float = 0.0

    @staticmethod
    def _load_api_key() -> str:
        """Load API key from credentials file or env var."""
        env_key = os.environ.get("MOLTBOOK_API_KEY")
        if env_key:
            return env_key

        if _CREDENTIALS_PATH.exists():
            data = json.loads(_CREDENTIALS_PATH.read_text())
            key = data.get("api_key", "")
            if key:
                return key

        raise ValueError(
            "No Moltbook API key found. Set MOLTBOOK_API_KEY env var "
            f"or save credentials to {_CREDENTIALS_PATH}"
        )

    @staticmethod
    def save_credentials(api_key: str, agent_name: str) -> Path:
        """Persist credentials to disk."""
        _CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        creds = {"api_key": api_key, "agent_name": agent_name}
        _CREDENTIALS_PATH.write_text(json.dumps(creds, indent=2))
        _CREDENTIALS_PATH.chmod(0o600)  # Owner-only read/write
        logger.info("Credentials saved to %s", _CREDENTIALS_PATH)
        return _CREDENTIALS_PATH

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[dict] = None,
        auth: bool = True,
    ) -> dict[str, Any]:
        """Make an HTTP request to the Moltbook API."""
        url = f"{_BASE_URL}{path}"

        # Zero-trust: verify we're only calling moltbook
        if not url.startswith("https://www.moltbook.com/"):
            raise ValueError(f"SECURITY: refusing to send request to {url}")

        # Rate limit pre-check
        if self._rate_remaining <= 0 and time.time() < self._rate_reset:
            wait = int(self._rate_reset - time.time()) + 1
            raise MoltbookRateLimited(retry_after=wait)

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if auth and self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        body = json.dumps(data).encode() if data else None
        req = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(req, timeout=_TIMEOUT) as resp:
                # Update rate limit tracking
                remaining = resp.headers.get("X-RateLimit-Remaining")
                if remaining is not None:
                    self._rate_remaining = int(remaining)
                reset = resp.headers.get("X-RateLimit-Reset")
                if reset is not None:
                    self._rate_reset = float(reset)

                return json.loads(resp.read().decode())

        except HTTPError as e:
            body_text = e.read().decode() if e.fp else "{}"
            try:
                err_data = json.loads(body_text)
            except json.JSONDecodeError:
                err_data = {}

            if e.code == 429:
                retry = int(e.headers.get("Retry-After", "60"))
                raise MoltbookRateLimited(retry_after=retry) from e

            raise MoltbookError(
                status=e.code,
                message=err_data.get("error", str(e)),
                hint=err_data.get("hint", ""),
            ) from e

    # ─── Registration ──────────────────────────────────────────

    def register(self, name: str, description: str) -> dict[str, Any]:
        """Register a new agent. No auth required."""
        result = self._request(
            "POST", "/agents/register",
            data={"name": name, "description": description},
            auth=False,
        )
        # Auto-save credentials
        agent = result.get("agent", {})
        api_key = agent.get("api_key", "")
        if api_key:
            self._api_key = api_key
            self.save_credentials(api_key, name)
        return result

    def check_status(self) -> dict[str, Any]:
        """Check claim status."""
        return self._request("GET", "/agents/status")

    # ─── Home / Dashboard ──────────────────────────────────────

    def get_home(self) -> dict[str, Any]:
        """Get the /home dashboard — single call for everything."""
        return self._request("GET", "/home")

    # ─── Posts ─────────────────────────────────────────────────

    def create_post(
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
        return self._request("POST", "/posts", data=payload)

    def get_feed(
        self, sort: str = "hot", limit: int = 25, cursor: str = ""
    ) -> dict[str, Any]:
        """Get the main feed."""
        params = f"?sort={sort}&limit={limit}"
        if cursor:
            params += f"&cursor={cursor}"
        return self._request("GET", f"/posts{params}")

    def get_post(self, post_id: str) -> dict[str, Any]:
        """Get a single post by ID."""
        return self._request("GET", f"/posts/{post_id}")

    def delete_post(self, post_id: str) -> dict[str, Any]:
        """Delete your post."""
        return self._request("DELETE", f"/posts/{post_id}")

    # ─── Comments ──────────────────────────────────────────────

    def create_comment(
        self, post_id: str, content: str, parent_id: str = ""
    ) -> dict[str, Any]:
        """Add a comment (or reply) to a post."""
        payload: dict[str, str] = {"content": content}
        if parent_id:
            payload["parent_id"] = parent_id
        return self._request("POST", f"/posts/{post_id}/comments", data=payload)

    def get_comments(
        self, post_id: str, sort: str = "best"
    ) -> dict[str, Any]:
        """Get comments on a post."""
        return self._request("GET", f"/posts/{post_id}/comments?sort={sort}")

    # ─── Voting ────────────────────────────────────────────────

    def upvote_post(self, post_id: str) -> dict[str, Any]:
        """Upvote a post."""
        return self._request("POST", f"/posts/{post_id}/upvote")

    def downvote_post(self, post_id: str) -> dict[str, Any]:
        """Downvote a post."""
        return self._request("POST", f"/posts/{post_id}/downvote")

    def upvote_comment(self, comment_id: str) -> dict[str, Any]:
        """Upvote a comment."""
        return self._request("POST", f"/comments/{comment_id}/upvote")

    # ─── Search ────────────────────────────────────────────────

    def search(
        self,
        query: str,
        search_type: str = "all",
        limit: int = 20,
        cursor: str = "",
    ) -> dict[str, Any]:
        """Semantic search across posts and comments."""
        from urllib.parse import quote_plus
        params = f"?q={quote_plus(query)}&type={search_type}&limit={limit}"
        if cursor:
            params += f"&cursor={cursor}"
        return self._request("GET", f"/search{params}")

    # ─── Verification ──────────────────────────────────────────

    def submit_verification(
        self, verification_code: str, answer: str
    ) -> dict[str, Any]:
        """Submit answer to a verification challenge."""
        return self._request(
            "POST", "/verify",
            data={"verification_code": verification_code, "answer": answer},
        )

    # ─── Profile ───────────────────────────────────────────────

    def get_me(self) -> dict[str, Any]:
        """Get your agent profile."""
        return self._request("GET", "/agents/me")

    def get_profile(self, agent_name: str) -> dict[str, Any]:
        """Get another agent's profile."""
        return self._request("GET", f"/agents/profile/{agent_name}")

    def update_profile(self, **fields: str) -> dict[str, Any]:
        """Update profile fields (bio, website, etc)."""
        return self._request("PATCH", "/agents/me", data=fields)

    # ─── Following ─────────────────────────────────────────────

    def follow(self, agent_name: str) -> dict[str, Any]:
        """Follow another molty."""
        return self._request("POST", f"/agents/{agent_name}/follow")

    def unfollow(self, agent_name: str) -> dict[str, Any]:
        """Unfollow a molty."""
        return self._request("DELETE", f"/agents/{agent_name}/follow")

    # ─── Submolts ──────────────────────────────────────────────

    def list_submolts(self) -> dict[str, Any]:
        """List all submolts."""
        return self._request("GET", "/submolts")

    def subscribe(self, submolt_name: str) -> dict[str, Any]:
        """Subscribe to a submolt."""
        return self._request("POST", f"/submolts/{submolt_name}/subscribe")

    # ─── DMs ───────────────────────────────────────────────────

    def get_dm_requests(self) -> dict[str, Any]:
        """Get pending DM requests."""
        return self._request("GET", "/agents/dm/requests")

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        """Read a DM conversation."""
        return self._request("GET", f"/agents/dm/conversations/{conversation_id}")

    def send_dm(self, conversation_id: str, message: str) -> dict[str, Any]:
        """Reply to a DM conversation."""
        return self._request(
            "POST", f"/agents/dm/conversations/{conversation_id}/send",
            data={"message": message},
        )

    # ─── Notifications ─────────────────────────────────────────

    def mark_notifications_read(self, post_id: str) -> dict[str, Any]:
        """Mark notifications for a post as read."""
        return self._request("POST", f"/notifications/read-by-post/{post_id}")

    # ─── Skill Updates ─────────────────────────────────────────

    def check_skill_version(self) -> str:
        """Check latest skill.md version."""
        from urllib.request import urlopen as _urlopen
        with _urlopen("https://www.moltbook.com/skill.json", timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("version", "unknown")

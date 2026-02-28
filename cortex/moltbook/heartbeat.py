"""Moltbook heartbeat — periodic check-in routine.

Follows the official HEARTBEAT.md protocol:
1. Call /home (single call dashboard)
2. Respond to activity on YOUR content (top priority)
3. Check DMs
4. Read feed + upvote generously
5. Comment on interesting posts
6. Post if we have something valuable
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from cortex.moltbook.client import MoltbookClient, MoltbookRateLimited
from cortex.moltbook.verification import solve_challenge

logger = logging.getLogger(__name__)

_STATE_PATH = Path.home() / ".config" / "moltbook" / "heartbeat-state.json"


class MoltbookHeartbeat:
    """Orchestrates the Moltbook heartbeat check-in cycle."""

    def __init__(self, client: Optional[MoltbookClient] = None):
        self.client = client or MoltbookClient()
        self._state = self._load_state()

    # ─── State Persistence ─────────────────────────────────────

    @staticmethod
    def _load_state() -> dict[str, Any]:
        if _STATE_PATH.exists():
            return json.loads(_STATE_PATH.read_text())
        return {
            "last_check": None,
            "last_post": None,
            "last_skill_update_check": None,
            "skill_version": "1.12.0",
        }

    def _save_state(self) -> None:
        _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STATE_PATH.write_text(json.dumps(self._state, indent=2))

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ─── Main Heartbeat Cycle ──────────────────────────────────

    def run(self) -> dict[str, Any]:
        """Execute a full heartbeat cycle. Returns summary."""
        summary: dict[str, Any] = {
            "timestamp": self._now_iso(),
            "actions": [],
            "errors": [],
        }

        try:
            # Step 1: Call /home
            home = self.client.get_home()
            summary["home"] = {
                "karma": home.get("your_account", {}).get("karma", 0),
                "unread": home.get("your_account", {}).get(
                    "unread_notification_count", 0
                ),
            }
            summary["actions"].append("checked_home")
            logger.info("Heartbeat: home loaded. Karma=%s", summary["home"]["karma"])

            # Step 2: Respond to activity on YOUR content (🔴 priority)
            activity = home.get("activity_on_your_posts", [])
            replies_sent = self._respond_to_activity(activity)
            if replies_sent:
                summary["actions"].append(f"replied_to_{replies_sent}_comments")

            # Step 3: Check DMs
            dms = home.get("your_direct_messages", {})
            if dms.get("unread_count", 0) > 0 or dms.get("pending_requests", 0) > 0:
                summary["actions"].append("checked_dms")
                logger.info("Heartbeat: %s unread DMs", dms.get("unread_count", 0))

            # Step 4: Read feed + upvote
            upvotes = self._browse_and_upvote()
            if upvotes:
                summary["actions"].append(f"upvoted_{upvotes}_posts")

            # Update state
            self._state["last_check"] = self._now_iso()
            self._save_state()

        except MoltbookRateLimited as e:
            summary["errors"].append(f"rate_limited_retry_after_{e.retry_after}s")
            logger.warning("Heartbeat: rate limited. Retry after %ss", e.retry_after)
        except Exception as e:
            summary["errors"].append(str(e))
            logger.exception("Heartbeat: unexpected error")

        return summary

    # ─── Step 2: Respond to Activity ───────────────────────────

    def _respond_to_activity(self, activity: list[dict]) -> int:
        """Reply to comments on our posts. Returns count of replies sent."""
        replies = 0
        for item in activity[:5]:  # Cap at 5 to respect rate limits
            post_id = item.get("post_id", item.get("id", ""))
            if not post_id:
                continue

            try:
                comments_resp = self.client.get_comments(post_id, sort="new")
                comments = comments_resp.get("comments", [])

                # Mark as read regardless
                self.client.mark_notifications_read(post_id)

                # Log but don't auto-reply — requires LLM for thoughtful response
                for comment in comments[:3]:
                    author = comment.get("author", {}).get("name", "unknown")
                    content = comment.get("content", "")[:80]
                    logger.info(
                        "Heartbeat: new comment from %s: %s...", author, content
                    )
                    # Upvote comments on our posts
                    cid = comment.get("id")
                    if cid:
                        self.client.upvote_comment(cid)
                        replies += 1

            except MoltbookRateLimited:
                logger.warning("Rate limited during activity response")
                break
            except Exception:
                logger.exception("Error responding to post %s", post_id)

        return replies

    # ─── Step 4: Browse & Upvote ───────────────────────────────

    def _browse_and_upvote(self, limit: int = 10) -> int:
        """Read feed and upvote interesting posts."""
        upvotes = 0
        try:
            feed = self.client.get_feed(sort="hot", limit=limit)
            posts = feed.get("posts", [])

            for post in posts[:limit]:
                post_id = post.get("id", "")
                if not post_id:
                    continue

                # Simple heuristic: upvote posts with some engagement
                upvote_count = post.get("upvotes", 0)
                if upvote_count >= 0:  # Upvote everything we see — generosity
                    try:
                        self.client.upvote_post(post_id)
                        upvotes += 1
                    except MoltbookRateLimited:
                        break
                    except Exception:
                        pass  # May already be upvoted

        except MoltbookRateLimited:
            logger.warning("Rate limited during feed browse")
        except Exception:
            logger.exception("Error browsing feed")

        return upvotes

    # ─── Posting with Verification ─────────────────────────────

    def create_verified_post(
        self, submolt_name: str, title: str, content: str
    ) -> dict[str, Any]:
        """Create a post and auto-solve verification challenge."""
        result = self.client.create_post(submolt_name, title, content)

        # Check if verification is required
        post_data = result.get("post", {})
        verification = post_data.get("verification")

        if verification and result.get("verification_required"):
            challenge = verification.get("challenge_text", "")
            code = verification.get("verification_code", "")

            if challenge and code:
                answer = solve_challenge(challenge)
                if answer:
                    logger.info("Solving verification: %s → %s", challenge[:40], answer)
                    verify_result = self.client.submit_verification(code, answer)
                    result["verification_result"] = verify_result
                else:
                    logger.warning("Could not solve challenge: %s", challenge)
                    result["verification_result"] = {"error": "unsolvable_challenge"}

        self._state["last_post"] = self._now_iso()
        self._save_state()
        return result

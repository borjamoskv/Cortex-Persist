import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .client import MoltbookClient, MoltbookRateLimited
from .verification import solve_challenge

try:
    from cortex.nexus_v8 import NexusWorldModel, moltbook_post_published

    _NEXUS = NexusWorldModel()
    _NEXUS_OK = True
except ImportError:
    _NEXUS_OK = False
    _NEXUS = None

logger = logging.getLogger(__name__)

_STATE_PATH = Path.home() / ".config" / "moltbook" / "heartbeat-state.json"


class MoltbookHeartbeat:
    """Async orchestrator for the Moltbook heartbeat check-in cycle.
    MEJORAlo 8.0: Zero blocking I/O for social presence.
    """

    def __init__(self, client: MoltbookClient | None = None):
        self.client = client or MoltbookClient()
        self._state = self._load_state()

    # ─── State Persistence ─────────────────────────────────────

    @staticmethod
    def _load_state() -> dict[str, Any]:
        if _STATE_PATH.exists():
            try:
                return json.loads(_STATE_PATH.read_text())
            except Exception:
                pass
        return {
            "last_check": None,
            "last_post": None,
            "last_skill_update_check": None,
            "skill_version": "1.12.0",
        }

    def _save_state(self) -> None:
        _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STATE_PATH.write_text(json.dumps(self._state, indent=2))
        _STATE_PATH.chmod(0o600)  # EFECTO-7: Owner-only read/write

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ─── Main Heartbeat Cycle ──────────────────────────────────

    async def run(self) -> dict[str, Any]:
        """Execute a full heartbeat cycle asynchronously. Returns summary."""
        summary: dict[str, Any] = {
            "timestamp": self._now_iso(),
            "actions": [],
            "errors": [],
        }

        try:
            # Multi-scale check: ensure identity is registered first
            await self.client.ensure_identity("flagship")

            # Step 1: Call /home
            home = await self.client.get_home()
            summary["home"] = {
                "karma": home.get("your_account", {}).get("karma", 0),
                "unread": home.get("your_account", {}).get("unread_notification_count", 0),
            }
            summary["actions"].append("checked_home")
            logger.info("Heartbeat: home loaded. Karma=%s", summary["home"]["karma"])

            # Step 2: Respond to activity on YOUR content (🔴 priority)
            activity = home.get("activity_on_your_posts", [])
            replies_sent = await self._respond_to_activity(activity)
            if replies_sent:
                summary["actions"].append(f"replied_to_{replies_sent}_comments")

            # Step 3: Check DMs
            dms = home.get("your_direct_messages", {})
            if dms.get("unread_count", 0) > 0 or dms.get("pending_requests", 0) > 0:
                summary["actions"].append("checked_dms")
                logger.info("Heartbeat: %s unread DMs", dms.get("unread_count", 0))

            # Step 4: Read feed + upvote
            upvotes = await self._browse_and_upvote()
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

    async def _respond_to_activity(self, activity: list[dict]) -> int:
        """Reply to comments on our posts. Returns count of replies sent."""
        replies = 0
        for item in activity[:5]:  # Cap at 5 to respect rate limits
            post_id = item.get("post_id", item.get("id", ""))
            if not post_id:
                continue

            try:
                comments_resp = await self.client.get_comments(post_id, sort="new")
                comments = comments_resp.get("comments", [])

                # Mark as read regardless
                await self.client.mark_notifications_read(post_id)

                # Log but don't auto-reply — requires LLM for thoughtful response
                for comment in comments[:3]:
                    author = comment.get("author", {}).get("name", "unknown")
                    content = comment.get("content", "")[:80]
                    logger.info("Heartbeat: new comment from %s: %s...", author, content)
                    # Upvote comments on our posts
                    cid = comment.get("id")
                    if cid:
                        await self.client.upvote_comment(cid)
                        replies += 1

            except MoltbookRateLimited:
                logger.warning("Rate limited during activity response")
                break
            except Exception:
                logger.exception("Error responding to post %s", post_id)

        return replies

    # ─── Step 4: Browse & Upvote ───────────────────────────────

    async def _browse_and_upvote(self, limit: int = 10) -> int:
        """Read feed and upvote interesting posts."""
        upvotes = 0
        try:
            feed = await self.client.get_feed(sort="hot", limit=limit)
            posts = feed.get("posts", [])

            for post in posts[:limit]:
                post_id = post.get("id", "")
                if not post_id:
                    continue

                # Simple heuristic: upvote everything we see — generosity
                try:
                    await self.client.upvote_post(post_id)
                    upvotes += 1
                except MoltbookRateLimited:
                    break
                except Exception:
                    logger.debug("Upvote failed for post %s", post_id)

        except MoltbookRateLimited:
            logger.warning("Rate limited during feed browse")
        except Exception:
            logger.exception("Error browsing feed")

        return upvotes

    # ─── Posting with Verification ─────────────────────────────

    async def create_verified_post(
        self, submolt_name: str, title: str, content: str
    ) -> dict[str, Any]:
        """Create a post and auto-solve verification challenge."""
        result = await self.client.create_post(submolt_name, title, content)

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
                    verify_result = await self.client.submit_verification(code, answer)
                    result["verification_result"] = verify_result
                else:
                    logger.warning("Could not solve challenge: %s", challenge)
                    result["verification_result"] = {"error": "unsolvable_challenge"}

        self._state["last_post"] = self._now_iso()
        self._save_state()

        # Nexus v8.1: emit POST_PUBLISHED mutation
        if _NEXUS_OK and _NEXUS:
            try:
                await moltbook_post_published(
                    _NEXUS,
                    agent_name="flagship",
                    submolt=submolt_name,
                    title=title,
                    karma_before=self._state.get("last_karma", 0.0),
                )
            except Exception as e:
                logger.debug("Nexus emit failed (non-blocking): %s", e)

        return result

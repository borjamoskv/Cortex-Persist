"""Moltbook Engagement Manager — Legitimate community interaction.

Manages smart replies, community discovery, and content curation
to build genuine organic presence on Moltbook.

Usage:
    mgr = EngagementManager(client)
    await mgr.respond_to_mentions()       # Reply to activity on your posts
    await mgr.discover_conversations()     # Find relevant threads to join
    await mgr.curate_feed()               # Upvote genuinely good content
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .client import MoltbookClient

logger = logging.getLogger(__name__)

_ENGAGEMENT_LOG_PATH = Path.home() / ".config" / "moltbook" / "engagement_log.json"

# Topics moskv-1 can authentically engage with
CORE_TOPICS = [
    "memory architectures",
    "agent systems",
    "sovereign AI",
    "cortex",
    "knowledge graphs",
    "AI infrastructure",
    "multi-agent coordination",
    "recursive systems",
    "developer tools",
    "autonomous systems",
]


@dataclass(slots=True)
class EngagementAction:
    """Log entry for an engagement action."""

    action_type: str  # reply | upvote | comment | discover
    target_id: str = ""
    content: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    success: bool = True
    error: str = ""


@dataclass(slots=True)
class EngagementLog:
    """Persistent engagement history to avoid duplicate interactions."""

    actions: list[EngagementAction] = field(default_factory=list)
    _interacted_ids: set[str] = field(default_factory=set, repr=False)

    def __post_init__(self) -> None:
        self._interacted_ids = {a.target_id for a in self.actions if a.success}

    def already_interacted(self, target_id: str) -> bool:
        return target_id in self._interacted_ids

    def log(self, action: EngagementAction) -> None:
        self.actions.append(action)
        if action.success:
            self._interacted_ids.add(action.target_id)

    def save(self, path: Path = _ENGAGEMENT_LOG_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Keep only last 500 actions to prevent unbounded growth
        recent = self.actions[-500:]
        data = [asdict(a) for a in recent]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        path.chmod(0o600)  # EFECTO-7: Owner-only read/write

    @classmethod
    def load(cls, path: Path = _ENGAGEMENT_LOG_PATH) -> EngagementLog:
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text())
            actions = [EngagementAction(**item) for item in raw]
            return cls(actions=actions)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Failed to load engagement log: %s", exc)
            return cls()


class EngagementManager:
    """Manages legitimate community engagement on Moltbook.

    Principles:
    - Only engage with content relevant to our expertise
    - Never spam — respect rate limits and interaction budgets
    - Add genuine value with every interaction
    - Log all actions to prevent duplicate engagement
    """

    def __init__(
        self,
        client: MoltbookClient | None = None,
        max_actions_per_cycle: int = 10,
    ) -> None:
        self.client = client or MoltbookClient()
        self.log = EngagementLog.load()
        self.max_actions = max_actions_per_cycle
        self._action_count = 0

    def _budget_available(self) -> bool:
        return self._action_count < self.max_actions

    # ── Respond to Activity ───────────────────────────────────────────────

    async def respond_to_mentions(self) -> dict[str, Any]:
        """Check and respond to activity on our posts (comments, replies).

        Returns summary of responses sent.
        """
        results: dict[str, Any] = {"responses": [], "errors": []}

        try:
            home = await self.client.get_home()
            activity = home.get("activity_on_posts", [])

            if not activity:
                results["message"] = "No new activity on posts."
                return results

            for item in activity:
                if not self._budget_available():
                    results["budget_exhausted"] = True
                    break

                post_id = item.get("post_id", "")
                if not post_id or self.log.already_interacted(f"reply_{post_id}"):
                    continue

                # Get comments on the post to find unreplied ones
                try:
                    comments_data = await self.client.get_comments(post_id)
                    comments = comments_data.get("comments", [])

                    # Find comments we haven't replied to
                    for comment in comments[:3]:  # Max 3 replies per post
                        comment_id = comment.get("id", "")
                        if self.log.already_interacted(f"reply_{comment_id}"):
                            continue

                        # Log the interaction as needing human-crafted reply
                        action = EngagementAction(
                            action_type="mention_detected",
                            target_id=f"reply_{comment_id}",
                            content=f"Comment on post {post_id}: {comment.get('content', '')[:100]}",
                        )
                        self.log.log(action)
                        self._action_count += 1

                        results["responses"].append({
                            "post_id": post_id,
                            "comment_id": comment_id,
                            "comment_preview": comment.get("content", "")[:100],
                            "author": comment.get("author", {}).get("name", "?"),
                            "action": "flagged_for_reply",
                        })

                except Exception as exc:
                    results["errors"].append(f"Post {post_id}: {exc}")

        except Exception as exc:
            results["errors"].append(f"Home fetch failed: {exc}")

        self.log.save()
        return results

    # ── Community Discovery ───────────────────────────────────────────────

    async def discover_conversations(
        self, topics: list[str] | None = None
    ) -> dict[str, Any]:
        """Find relevant conversations to participate in.

        Searches for posts matching our expertise areas and returns
        opportunities for genuine contribution.
        """
        search_topics = topics or CORE_TOPICS[:5]
        results: dict[str, Any] = {"opportunities": [], "topics_searched": []}

        for topic in search_topics:
            if not self._budget_available():
                break

            try:
                search_result = await self.client.search(
                    topic, search_type="posts", limit=5
                )
                found = search_result.get("results", [])

                for post in found:
                    post_id = post.get("id", "")
                    if self.log.already_interacted(f"disc_{post_id}"):
                        continue

                    similarity = post.get("similarity", 0)
                    if similarity < 0.5:  # Only high-relevance results
                        continue

                    results["opportunities"].append({
                        "post_id": post_id,
                        "title": post.get("title", ""),
                        "author": post.get("author", {}).get("name", "?"),
                        "similarity": similarity,
                        "topic_matched": topic,
                        "comment_count": post.get("comment_count", 0),
                    })

                    # Log discovery (not interaction yet)
                    self.log.log(EngagementAction(
                        action_type="discover",
                        target_id=f"disc_{post_id}",
                        content=f"Found via '{topic}': {post.get('title', '')[:60]}",
                    ))
                    self._action_count += 1

                results["topics_searched"].append(topic)

            except Exception as exc:
                logger.warning("Search for '%s' failed: %s", topic, exc)

        # Sort by relevance
        results["opportunities"].sort(
            key=lambda o: o.get("similarity", 0), reverse=True
        )

        self.log.save()
        return results

    # ── Content Curation ──────────────────────────────────────────────────

    async def curate_feed(self, limit: int = 15) -> dict[str, Any]:
        """Browse feed and upvote genuinely good content.

        Uses keyword matching against our expertise to identify
        posts worth supporting. Only upvotes quality content.
        """
        results: dict[str, Any] = {"upvoted": [], "skipped": 0}

        try:
            feed = await self.client.get_feed(sort="hot", limit=limit)
            posts = feed.get("posts", [])

            for post in posts:
                if not self._budget_available():
                    break

                post_id = post.get("id", "")
                if self.log.already_interacted(f"vote_{post_id}"):
                    results["skipped"] += 1
                    continue

                title = (post.get("title", "") + " " + post.get("content", "")).lower()

                # Only upvote posts relevant to our domain
                relevant = any(topic in title for topic in CORE_TOPICS)
                quality = post.get("comment_count", 0) >= 1 or post.get("upvotes", 0) >= 2

                if relevant and quality:
                    try:
                        await self.client.upvote_post(post_id)
                        self.log.log(EngagementAction(
                            action_type="upvote",
                            target_id=f"vote_{post_id}",
                            content=post.get("title", "")[:60],
                        ))
                        results["upvoted"].append({
                            "post_id": post_id,
                            "title": post.get("title", ""),
                        })
                        self._action_count += 1
                    except Exception as exc:
                        self.log.log(EngagementAction(
                            action_type="upvote",
                            target_id=f"vote_{post_id}",
                            success=False,
                            error=str(exc),
                        ))
                else:
                    results["skipped"] += 1

        except Exception as exc:
            results["error"] = str(exc)

        self.log.save()
        return results

    # ── Full Engagement Cycle ─────────────────────────────────────────────

    async def run_cycle(self) -> dict[str, Any]:
        """Execute a full engagement cycle: respond → discover → curate.

        This is the main entry point for the engagement manager.
        Should be run periodically (e.g., every few hours via heartbeat).
        """
        logger.info("🦞 Starting engagement cycle...")

        cycle_results: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 1. Respond to mentions first (highest priority)
        cycle_results["mentions"] = await self.respond_to_mentions()

        # 2. Discover new conversations
        cycle_results["discovery"] = await self.discover_conversations()

        # 3. Curate feed
        cycle_results["curation"] = await self.curate_feed()

        cycle_results["total_actions"] = self._action_count
        logger.info(
            "🦞 Engagement cycle complete: %d actions", self._action_count
        )

        return cycle_results

    # ── Introspection ─────────────────────────────────────────────────────

    def engagement_summary(self) -> dict[str, Any]:
        """Get summary of all engagement activity."""
        from collections import Counter

        type_counts = Counter(a.action_type for a in self.log.actions)
        success_rate = (
            sum(1 for a in self.log.actions if a.success) / max(len(self.log.actions), 1)
        )

        return {
            "total_actions": len(self.log.actions),
            "action_types": dict(type_counts.most_common()),
            "success_rate": f"{success_rate * 100:.1f}%",
            "unique_targets": len(self.log._interacted_ids),
        }

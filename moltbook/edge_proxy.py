from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .client import MoltbookClient

logger = logging.getLogger("cortex.moltbook.proxy")


class MoltbookEdgeProxy:
    """
    Edge Proxy for Moltbook API (Ω₂).
    Handles real-time sync with fallback to CORTEX intervention cache.
    Eliminates dependency on Manual Intervention by bridging API state.
    (Ghost 3193 resolution)
    """

    def __init__(self, client: MoltbookClient):
        self.client = client
        self._cache: dict[str, Any] = {}

    async def get_post_sync(self, post_id: str) -> dict[str, Any]:
        """Get post with real-time sync and cache fallback."""
        try:
            post = await self.client.get_post(post_id)
            self._cache[post_id] = post
            return post
        except Exception as e:
            logger.warning("🛡️ [MOLTBOOK-PROXY] API Fallback active for %s: %s", post_id, e)
            # Ω₃: Fallback to CORTEX intervention cache if present
            return self._cache.get(post_id, {"status": "error", "reason": "moltbook_offline"})

    async def sync_feed(self, sort: str = "hot", limit: int = 25) -> dict[str, Any]:
        """Sincronía en masa del feed para reducir latencia."""
        try:
            feed = await self.client.get_feed(sort=sort, limit=limit)
            for post in feed.get("posts", []):
                pid = post.get("id")
                if pid:
                    self._cache[pid] = post
            return feed
        except Exception as e:
            logger.error("🛡️ [MOLTBOOK-PROXY] Feed sync failed: %s", e)
            return {"posts": list(self._cache.values())[:limit]}

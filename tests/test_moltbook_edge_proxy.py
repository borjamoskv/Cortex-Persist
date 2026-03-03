"""Tests for MoltbookEdgeProxy — cache fallback resilience (Ω₂)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from moltbook.edge_proxy import MoltbookEdgeProxy


def _make_mock_client():
    """Create a MoltbookClient mock with async methods."""
    client = MagicMock()
    client.get_post = AsyncMock()
    client.get_feed = AsyncMock()
    return client


class TestEdgeProxy:
    """Cache fallback and feed sync."""

    @pytest.mark.asyncio
    async def test_get_post_populates_cache(self):
        client = _make_mock_client()
        post_data = {"id": "post-1", "title": "Sovereign Memory", "upvotes": 42}
        client.get_post.return_value = post_data

        proxy = MoltbookEdgeProxy(client)
        result = await proxy.get_post_sync("post-1")

        assert result == post_data
        assert proxy._cache["post-1"] == post_data

    @pytest.mark.asyncio
    async def test_get_post_fallback_on_error(self):
        client = _make_mock_client()
        cached_post = {"id": "post-2", "title": "Cached Post"}

        proxy = MoltbookEdgeProxy(client)
        proxy._cache["post-2"] = cached_post

        # Simulate API failure
        client.get_post.side_effect = ConnectionError("Moltbook offline")
        result = await proxy.get_post_sync("post-2")

        assert result == cached_post  # Falls back to cache

    @pytest.mark.asyncio
    async def test_sync_feed_caches_posts(self):
        client = _make_mock_client()
        feed = {
            "posts": [
                {"id": "f1", "title": "Post One"},
                {"id": "f2", "title": "Post Two"},
                {"id": "f3", "title": "Post Three"},
            ]
        }
        client.get_feed.return_value = feed

        proxy = MoltbookEdgeProxy(client)
        result = await proxy.sync_feed()

        assert len(result["posts"]) == 3
        assert "f1" in proxy._cache
        assert "f2" in proxy._cache
        assert "f3" in proxy._cache
        assert proxy._cache["f2"]["title"] == "Post Two"

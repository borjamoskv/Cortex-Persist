from __future__ import annotations

import logging
import os
from typing import TypedDict

logger = logging.getLogger(__name__)

# Note: PRAW must be installed (pip install praw)
try:
    import praw
except ImportError:
    praw = None


class SearchMentionsResult(TypedDict):
    id: str
    subreddit: str
    title: str
    selftext: str
    url: str
    score: int


async def reddit_search_mentions(query: str, limit: int = 10) -> list[SearchMentionsResult]:
    """
    Searches Reddit for mentions of a specific query.
    Requires REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, and REDDIT_USER_AGENT in .env.
    """
    if praw is None:
        raise RuntimeError(
            "The 'praw' library is not installed. Please install it to use Reddit tools."
        )

    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "CORTEX-Persist Autonomous Agent v0.3.0b1")

    if not client_id or not client_secret:
        raise ValueError("Missing REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET environment variables")

    # In a fully async system, PRAW (which is sync) should be wrapped in an async executor (e.g. asyncio.to_thread)
    # Using Async PRAW (apraw) would be ideal, but standard PRAW is more common.
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )

    results = []
    logger.info("Searching Reddit for query: %s", query)
    for submission in reddit.subreddit("all").search(query, limit=limit):
        results.append(
            {
                "id": submission.id,
                "subreddit": submission.subreddit.display_name,
                "title": submission.title,
                "selftext": submission.selftext[:500] + "..."
                if len(submission.selftext) > 500
                else submission.selftext,
                "url": submission.url,
                "score": submission.score,
            }
        )

    return results


async def reddit_publish_promotion(subreddit: str, title: str, text: str) -> dict[str, str]:
    """
    Publishes a promotion post to a given subreddit.
    Requires REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT, REDDIT_USERNAME, and REDDIT_PASSWORD.
    """
    if praw is None:
        raise RuntimeError(
            "The 'praw' library is not installed. Please install it to use Reddit tools."
        )

    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "CORTEX-Persist Autonomous Agent v0.3.0b1")
    username = os.getenv("REDDIT_USERNAME")
    password = os.getenv("REDDIT_PASSWORD")

    if not all([client_id, client_secret, username, password]):
        raise ValueError(
            "Missing required Reddit credentials. Need REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, "
            "REDDIT_USERNAME, and REDDIT_PASSWORD."
        )

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        username=username,
        password=password,
    )

    logger.info("Publishing promotion to r/%s: %s", subreddit, title)

    # Actually submit the post
    submission = reddit.subreddit(subreddit).submit(title, selftext=text)

    return {
        "status": "published",
        "url": submission.url,
        "id": submission.id,
    }


import typing


class RedditSearchTool:
    """Tool wrapper for searching Reddit mentions."""

    @property
    def name(self) -> str:
        return "reddit_search_mentions"

    async def execute(self, **kwargs: typing.Any) -> typing.Any:
        query = kwargs.get("query")
        limit = kwargs.get("limit", 10)
        if not query or not isinstance(query, str):
            raise ValueError("Query is required and must be a string")
        return await reddit_search_mentions(query=query, limit=int(limit))


class RedditPublishTool:
    """Tool wrapper for publishing Reddit promotions."""

    @property
    def name(self) -> str:
        return "reddit_publish_promotion"

    async def execute(self, **kwargs: typing.Any) -> typing.Any:
        subreddit = kwargs.get("subreddit")
        title = kwargs.get("title")
        text = kwargs.get("text")
        if not all([isinstance(subreddit, str), isinstance(title, str), isinstance(text, str)]):
            raise ValueError("subreddit, title, and text are required and must be strings")
        # pyright check override since we validated they are strings
        return await reddit_publish_promotion(
            subreddit=str(subreddit), title=str(title), text=str(text)
        )

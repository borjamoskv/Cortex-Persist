import asyncio

from cortex.services.moltbook import MoltbookService


async def get_id():
    service = MoltbookService()
    feed = await service.get_feed(limit=1)
    posts = feed.get("posts", [])
    if posts:
        print("POST_ID:", posts[0].get("id"))
    else:
        print("No posts found")

asyncio.run(get_id())

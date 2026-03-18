import asyncio
from cortex.extensions.moltbook.client import MoltbookClient

async def get_claim():
    client = MoltbookClient()
    print("Checking status...")
    status = await client.check_status()
    print(status)
    print("Checking /agents/me...")
    me = await client.get_me()
    print(me)
    await client.close()

asyncio.run(get_claim())

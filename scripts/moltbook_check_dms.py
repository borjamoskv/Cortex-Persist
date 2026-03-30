import asyncio

from cortex.extensions.moltbook.client import MoltbookClient


async def check_dms():
    client = MoltbookClient()
    print("Checking DM requests...")
    try:
        reqs = await client.get_dm_requests()
        print("Requests:", reqs)
    except Exception as e:
        print("Error requests:", e)

    print("Checking Conversations...")
    try:
        # We don't have a list_conversations method in client.py, we only have get_conversation(id)
        # But maybe we can just query the endpoint manually:
        convs = await client._request("GET", "/agents/dm")
        print("Conversations:", convs)
    except Exception as e:
        print("Error convs:", e)

    await client.close()

if __name__ == "__main__":
    asyncio.run(check_dms())

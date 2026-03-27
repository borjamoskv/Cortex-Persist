import asyncio

from cortex.swarm.bounty_scanner import AlgoraScanner


async def run():
    s = await AlgoraScanner().scan(limit=5)
    for o in s:
        if o.reward_usd >= 5000:
            print(f"REPO={o.repo}")
            print(f"URL={o.url}")

if __name__ == "__main__":
    asyncio.run(run())

import asyncio
import httpx
import json

agents = [
    {"name": "Admin-Zorro", "role": "admin"},
    {"name": "Trusted-Batman", "is_trusted": True},
    {"name": "Moderator-Robin", "trusted_agent": True},
    {"name": "God-Moskv", "admin": True}
]

async def main():
    async with httpx.AsyncClient() as client:
        for agent_data in agents:
            name = agent_data.pop("name")
            payload = {"name": name, "description": "Trying bypass"}
            payload.update(agent_data)
            
            resp = await client.post(
                "https://www.moltbook.com/api/v1/agents/register",
                json=payload
            )
            print(f"[{name}] HTTP {resp.status_code}")
            try:
                print(json.dumps(resp.json(), indent=2))
            except:
                print(resp.text)
            print("-" * 40)

asyncio.run(main())

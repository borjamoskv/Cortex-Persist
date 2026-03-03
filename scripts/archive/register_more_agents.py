import asyncio
import httpx
import random

agents = ["Joker-Moskv", "Bane-Moskv", "Riddler-Moskv", "Penguin-Moskv", "Catwoman-Moskv"]

async def main():
    for name in agents:
        async with httpx.AsyncClient() as client:
            fake_ip = f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
            headers = {
                "X-Forwarded-For": fake_ip,
                "X-Real-IP": fake_ip,
                "True-Client-IP": fake_ip
            }
            resp = await client.post(
                "https://www.moltbook.com/api/v1/agents/register",
                headers=headers,
                json={"name": name, "description": f"Enjambre infiltrador: {name}"}
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                print(f"Agent: {name}")
                print(f"API Key: {data['agent']['api_key']}")
                print(f"Claim URL: {data['agent']['claim_url']}")
                print("-" * 40)
            else:
                print(f"Failed for {name}: {resp.status_code} {resp.text}")

asyncio.run(main())

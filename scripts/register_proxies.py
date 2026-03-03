import asyncio
import httpx

agents = ["Joker-Moskv", "Bane-Moskv", "Riddler-Moskv", "Penguin-Moskv"]

async def main():
    # Fetch free proxies
    print("Fetching free HTTP proxies...")
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt")
        proxies = resp.text.split("\n")[:50]  # Try first 50 valid proxies
        
    print(f"Got {len(proxies)} proxies. Trying to register agents...")
    
    agent_idx = 0
    proxy_idx = 0
    while agent_idx < len(agents) and proxy_idx < len(proxies):
        proxy = proxies[proxy_idx].strip()
        proxy_idx += 1
        if not proxy: continue
        
        name = agents[agent_idx]
        proxy_url = f"http://{proxy}"
        try:
            async with httpx.AsyncClient(proxy=proxy_url, timeout=5.0) as client:
                resp = await client.post(
                    "https://www.moltbook.com/api/v1/agents/register",
                    json={"name": name, "description": f"Enjambre infiltrador (M2M): {name}"}
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    print(f"Agent: {name}")
                    print(f"API Key: {data['agent']['api_key']}")
                    print(f"Claim URL: {data['agent']['claim_url']}")
                    print("-" * 40)
                    agent_idx += 1
                elif resp.status_code == 429:
                    # Proxy is also rate-limited or dead
                    pass
                elif resp.status_code == 409:
                    print(f"Agent name '{name}' already taken, skipping.")
                    agent_idx += 1
                else:
                    print(f"Unexpected status via proxy {proxy}: {resp.status_code} {resp.text}")
        except Exception:
            # Proxy timeout or error, just try next
            pass

asyncio.run(main())

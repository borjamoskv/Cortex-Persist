import asyncio
import logging
import random
import os
from pathlib import Path
import httpx
from cortex.moltbook.client import MoltbookClient
from cortex.moltbook.identity_vault import IdentityVault

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🔥 %(levelname)s: %(message)s")
logger = logging.getLogger("MassRegistrationV3")

async def get_proxies():
    """Fetch high-quality-ish free proxies."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt")
            proxies = [f"socks4://{p}" for p in resp.text.split("\n") if p.strip()]
            random.shuffle(proxies)
            return proxies
    except Exception as e:
        logger.error(f"Failed to fetch proxies: {e}")
        return []

async def register_with_proxy(name, proxy, vault):
    """Attempt registration via proxy."""
    creds_path = Path(f"/Users/borjafernandezangulo/cortex/cortex/moltbook/creds_{name.lower()}.json")
    client = MoltbookClient(stealth=True, credentials_path=creds_path, proxy=proxy)
    
    try:
        logger.info(f"🔥 [{name}] Attempting registration via {proxy}...")
        await asyncio.sleep(random.uniform(1, 4))
        
        result = await client.register(name, description=f"MOSKV-1 Legion Node | {name}")
        agent = result.get("agent", {})
        
        if agent.get("api_key"):
            logger.info(f"✅ [{name}] SUCCESS! API Key: {agent['api_key'][:10]}...")
            
            vault.store_identity(
                name=name,
                api_key=agent["api_key"],
                metadata={
                    "claim_url": agent.get("claim_url"),
                    "proxy_used": proxy,
                    "status": "pending_claim",
                    "generator": "MassRegistrationV3"
                }
            )
            return agent
    except Exception as e:
        logger.warning(f"❌ [{name}] Failed via {proxy}: {e}")
    finally:
        await client.close()
    return None

async def main():
    vault = IdentityVault()
    proxies = await get_proxies()
    
    if not proxies:
        logger.error("No proxies available. Trying local (likely to fail but worth a shot)...")
        proxies = [None]

    targets = [f"drone-{random.randint(1000, 9999)}" for _ in range(5)]
    
    successful = []
    proxy_idx = 0
    
    logger.info("🚀 INICIANDO ASALTO DE REGISTRO MASIVO V3 🚀")
    
    for name in targets:
        attempts = 0
        while attempts < 20 and proxy_idx < len(proxies):
            proxy = proxies[proxy_idx]
            proxy_idx += 1
            attempts += 1
            
            agent = await register_with_proxy(name, proxy, vault)
            if agent:
                successful.append(agent)
                break
            
            await asyncio.sleep(0.5)

    logger.info(f"🎯 Total successful: {len(successful)}/5")
    
    if successful:
        print("\n" + "="*50)
        print("MOLTBOOK CLAIM HANDOFF")
        print("="*50)
        for agent in successful:
            print(f"Agent: {agent['name']} | URL: {agent['claim_url']}")
        print("="*50)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import logging
import random
import os
import json
from pathlib import Path
import httpx
from cortex.moltbook.client import MoltbookClient
from cortex.moltbook.identity_vault import IdentityVault
from cortex.network.real_mail import RealMail

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🔱 %(levelname)s: %(message)s")
logger = logging.getLogger("SovereignRegistration")

async def get_proxies():
    """Fetch high-quality SOCKS4 proxies."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt")
            proxies = [f"socks4://{p}" for p in resp.text.split("\n") if p.strip()]
            random.shuffle(proxies)
            return proxies
    except Exception as e:
        logger.error(f"Failed to fetch proxies: {e}")
        return []

async def register_sovereign_agent(name, proxy, vault, mail_engine):
    """Register agent with real email, stored password, and proxy rotation."""
    creds_path = Path(f"/Users/borjafernandezangulo/cortex/cortex/moltbook/creds_{name.lower()}.json")
    client = MoltbookClient(stealth=True, credentials_path=creds_path, proxy=proxy)
    
    try:
        # 1. Manifold de Email Real
        mail_creds = await mail_engine.get_email_for_agent(name)
        email = mail_creds["email"]
        password = mail_creds["password"]
        logger.info(f"🔱 [{name}] Generada Identidad Real: {email}")

        # 2. Registration Strike
        logger.info(f"📡 [{name}] Intentando registro vía {proxy or 'LOCAL'}...")
        await asyncio.sleep(random.uniform(2, 6)) # Sovereign Jitter
        
        result = await client.register(
            name=name, 
            description=f"Sovereign Intelligence Node | Alpha-Series : {name}",
            email=email
        )
        agent = result.get("agent", {})
        
        if agent.get("api_key"):
            logger.info(f"✅ [{name}] SOBERANÍA ALCANZADA. Key: {agent['api_key'][:12]}...")
            
            # 3. Persistencia en Bóveda (Encrypting password)
            vault.store_identity(
                name=name,
                api_key=agent["api_key"],
                email=email,
                email_password=password,
                metadata={
                    "claim_url": agent.get("claim_url"),
                    "proxy_used": proxy,
                    "status": "pending_verification",
                    "creation_strategy": "sovereign_manifold_v1"
                }
            )
            return {**agent, "email": email, "password": password}
    except Exception as e:
        logger.warning(f"❌ [{name}] Strike Fallido: {e}")
    finally:
        await client.close()
    return None

async def main():
    vault = IdentityVault()
    mail_engine = RealMail(provider="subaddress") # Default to subaddress (Gmail +)
    proxies = await get_proxies()
    
    if not proxies:
        logger.warning("No proxies found. Using local network (Risk: 429).")
        proxies = [None]

    # New Legion to deploy
    targets = ["Catwoman-Moskv", "Scarecrow-Moskv", "Ra-al-Ghul-Moskv"]
    
    successful = []
    proxy_idx = 0
    
    print("\n" + "═"*60)
    print("  🚀 SOVEREIGN REGISTRATION PROTOCOL (v5.5) 🚀")
    print("  Emails: Real Manifold | Storage: IdentityVault (Encrypted)")
    print("═"*60 + "\n")
    
    for name in targets:
        # Retry with different proxies if needed
        attempts = 0
        while attempts < 15 and proxy_idx < len(proxies):
            proxy = proxies[proxy_idx]
            proxy_idx += 1
            attempts += 1
            
            agent = await register_sovereign_agent(name, proxy, vault, mail_engine)
            if agent:
                successful.append(agent)
                break
            
            # Wait between proxy switches
            await asyncio.sleep(1)

    print("\n" + "═"*60)
    print("  🎯 REGISTRATION DEPLOYMENT SUMMARY")
    print("═"*60)
    for agent in successful:
        print(f"  Agent : {agent['name']}")
        print(f"  Email : {agent['email']}")
        print(f"  Pass  : [STORED IN VAULT]")
        print(f"  Claim : {agent['claim_url']}")
        print("  " + "─"*50)
    print(f"  Total: {len(successful)}/{len(targets)}")
    print("═"*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())

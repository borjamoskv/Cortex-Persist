"""Mass Registration Attack v2 — Real Email Integration.
Uses RealMail engine to provide non-temporal emails to agents.
"""

import asyncio
import logging
import random
import os
from pathlib import Path
import click
from cortex.moltbook.client import MoltbookClient
from cortex.moltbook.identity_vault import IdentityVault
from cortex.network.real_mail import RealMail

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🔥 %(levelname)s: %(message)s")
logger = logging.getLogger("MassRegistrationReal")

async def register_with_real_email(name, proxy, vault, mail_engine):
    """Attempt registration with real email and proxy."""
    creds_path = Path(f"/Users/borjafernandezangulo/cortex/cortex/moltbook/creds_{name.lower()}.json")
    client = MoltbookClient(stealth=True, credentials_path=creds_path, proxy=proxy)
    
    try:
        # 1. Get real email
        email = await mail_engine.get_email_for_agent(name)
        logger.info(f"🔥 [{name}] Using real email: {email}")
        
        # 2. Register
        logger.info(f"📡 [{name}] Attempting registration via {proxy}...")
        await asyncio.sleep(random.uniform(2, 5))
        
        result = await client.register(name, description=f"Sovereign Agent: {name}", email=email)
        agent = result.get("agent", {})
        
        if agent.get("api_key"):
            logger.info(f"✅ [{name}] SUCCESS! API Key: {agent['api_key']}")
            
            vault.store_identity(
                name=name,
                api_key=agent["api_key"],
                email=email,
                metadata={
                    "claim_url": agent.get("claim_url"),
                    "proxy_used": proxy,
                    "status": "pending_verification"
                }
            )
            return agent
    except Exception as e:
        logger.warning(f"❌ [{name}] Failed: {e}")
    finally:
        await client.close()
    return None

@click.command()
@click.option("--provider", default="subaddress", help="Email provider: subaddress, addy")
@click.option("--domain", default="", help="Custom domain (for Addy.io)")
def main(provider, domain):
    vault = IdentityVault()
    mail_engine = RealMail(provider=provider, domain=domain)
    
    targets = [
        "Joker-Real", "Bane-Real", "Riddler-Real", "Penguin-Real"
    ]
    
    # Use proxies if available
    proxies = [""] # Fallback to local for demo, or add proxy logic
    
    async def run_attack():
        successful = []
        for name in targets:
            agent = await register_with_real_email(name, None, vault, mail_engine)
            if agent:
                successful.append(agent)
                
        print("\n" + "="*50)
        print("MOLTBOOK REAL EMAIL HANDOFF")
        print("="*50)
        for agent in successful:
            print(f"Agent: {agent['name']} | Email: {agent.get('email', 'N/A')}")
        print("="*50)

    asyncio.run(run_attack())

if __name__ == "__main__":
    main()

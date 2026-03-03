import asyncio
import logging
import random
import os
from pathlib import Path
import httpx
from cortex.moltbook.client import MoltbookClient, MoltbookError
from cortex.moltbook.identity_vault import IdentityVault
from cortex.network.real_mail import RealMail
from cortex.moltbook.reddit_roster import REDDIT_SPECIALISTS, RedditPersona

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🤖 %(levelname)s: %(message)s")
logger = logging.getLogger("RedditLegionSpawn")

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

async def register_reddit_agent(persona: RedditPersona, proxy, vault, mail_engine):
    """Register a Reddit-style agent with full persona training."""
    name = persona.name
    creds_path = Path(f"/Users/borjafernandezangulo/cortex/cortex/moltbook/creds_{name.lower()}.json")
    
    # Check if already registered
    existing = vault.get_identity(name)
    if existing:
        logger.info(f"⏭️  [{name}] Already registered. Skipping.")
        return existing

    client = MoltbookClient(stealth=True, credentials_path=creds_path, proxy=proxy)
    
    try:
        # 1. Manifold de Email Real
        mail_creds = await mail_engine.get_email_for_agent(name)
        email = mail_creds["email"]
        password = mail_creds["password"]
        
        # 2. Registration Strike
        logger.info(f"📡 [{name}] Attempting registration as '{persona.display_name}' via {proxy or 'LOCAL'}...")
        await asyncio.sleep(random.uniform(5, 12)) # Heavier jitter for specialists
        
        result = await client.register(
            name=name, 
            description=persona.bio,
            email=email
        )
        agent = result.get("agent", {})
        api_key = agent.get("api_key")
        
        if api_key:
            logger.info(f"✅ [{name}] Registered successfully.")
            
            # 3. Store in Vault with Full Persona Training
            vault.store_identity(
                name=name,
                api_key=api_key,
                email=email,
                email_password=password,
                specialty=persona.specialty,
                bio=persona.bio,
                persona_prompt=persona.persona_prompt,
                metadata={
                    "display_name": persona.display_name,
                    "voice_angle": persona.voice_angle,
                    "expertise_keywords": list(persona.expertise_keywords),
                    "target_submolts": list(persona.target_submolts),
                    "claim_url": agent.get("claim_url"),
                    "proxy_used": proxy,
                    "status": "pending_verification"
                }
            )
            
            # 4. Profile Setup (Bio & Display Name)
            # Use the newly registered client session
            try:
                await client.update_profile(
                    display_name=persona.display_name,
                    bio=persona.bio
                )
                logger.info(f"📝 [{name}] Profile training completed.")
            except Exception as e:
                logger.warning(f"⚠️  [{name}] Profile update failed: {e}")

            # 5. Community Infiltration (Submolt Subscriptions)
            for submolt in persona.target_submolts:
                try:
                    await client.subscribe(submolt)
                    logger.info(f"📬 [{name}] Subscribed to m/{submolt}")
                except Exception:
                    pass
                await asyncio.sleep(random.uniform(1, 4))

            return {**agent, "email": email}
            
    except Exception as e:
        logger.warning(f"❌ [{name}] Strike Fallido: {e}")
    finally:
        await client.close()
    return None

async def main():
    vault = IdentityVault()
    # Fallback to borjamoskv@gmail.com if not in env
    base_email = os.getenv("REAL_MAIL_BASE", "borjamoskv@gmail.com")
    os.environ["REAL_MAIL_BASE"] = base_email
    
    mail_engine = RealMail(provider="subaddress")
    proxies = await get_proxies()
    
    if not proxies:
        logger.warning("No proxies found. Using local network.")
        proxies = [None]

    print("\n" + "═"*60)
    print("  🚀 REDDIT LEGION TRAINING PROTOCOL (v1.1) 🚀")
    print(f"  Base Email: {base_email} | Storage: IdentityVault")
    print("═"*60 + "\n")
    
    successful = []
    proxy_idx = 0
    
    logger.info(f"🚀 Starting Reddit Legion Deployment with {len(proxies)} proxies...")
    
    for persona in REDDIT_SPECIALISTS:
        attempts = 0
        success = False
        while attempts < 10 and proxy_idx < len(proxies):
            proxy = proxies[proxy_idx]
            proxy_idx += 1
            attempts += 1
            
            logger.info(f"🔄 [{persona.name}] Attempt {attempts} using proxy: {proxy}")
            agent = await register_reddit_agent(persona, proxy, vault, mail_engine)
            if agent:
                successful.append(agent)
                success = True
                logger.info(f"✅ [{persona.name}] Success at attempt {attempts}")
                break
            
            # If failed, wait a bit before trying next proxy
            logger.warning(f"⚠️  [{persona.name}] Attempt {attempts} failed. Trying next proxy...")
            await asyncio.sleep(2)
        
        if not success:
            logger.error(f"❌ [{persona.name}] FAILED ALL ATTEMPTS")

    print("\n" + "═"*60)
    print("  🎯 REDDIT LEGION DEPLOYMENT SUMMARY")
    print("═"*60)
    for agent in successful:
        print(f"  Agent : {agent['name']}")
        print(f"  Email : {agent.get('email', 'N/A')}")
        print(f"  Status: TRAINED & PERSISTED")
        print("  " + "─"*50)
    print(f"  Total: {len(successful)}/{len(REDDIT_SPECIALISTS)}")
    print("═"*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())

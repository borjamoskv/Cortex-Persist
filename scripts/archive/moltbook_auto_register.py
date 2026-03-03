import asyncio
import secrets
import string
import logging
import random
from cortex.moltbook.client import MoltbookClient
from cortex.network.temp_mail import TempMail
from cortex.moltbook.identity_vault import IdentityVault

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("AutoRegister")

async def register_one(vault: IdentityVault):
    name_suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6))
    agent_name = f"legion-moskv-{name_suffix}"
    
    mail = TempMail()
    client = MoltbookClient() # Default client, no key yet
    
    try:
        # AIROS-Ω: Resilience loop for email creation
        email = None
        for attempt in range(3):
            try:
                logger.info(f"[*] Creating email for {agent_name} (attempt {attempt+1})...")
                email = await mail.create_account()
                logger.info(f"[+] Email created: {email}")
                break
            except Exception as e:
                if attempt == 2: raise
                wait = (attempt + 1) * 30 + random.uniform(10, 30)
                logger.warning(f"[-] Email creation failed, retrying in {wait:.1f}s: {e}")
                await asyncio.sleep(wait)
        
        if not email:
            logger.error(f"[-] Could not create email for {agent_name}")
            return None

        logger.info(f"[*] Registering {agent_name} on Moltbook...")
        reg_result = await client.register(
            name=agent_name,
            description=f"MOSKV-1 Legion Node | {agent_name}",
            email=email
        )
        
        agent_data = reg_result.get("agent", {})
        api_key = agent_data.get("api_key")
        
        if api_key:
            logger.info(f"[SUCCESS] Registered {agent_name}. Key: {api_key[:10]}...")
            return agent_name
        else:
            logger.error(f"[-] Registration failed for {agent_name}: {reg_result}")
            
    except Exception as e:
        logger.error(f"[!] Error during registration ({agent_name}): {e}")
    finally:
        await mail.close()
        await client.close()

async def scale_legion(count: int = 5):
    vault = IdentityVault()
    successful_count = 0
    
    # Sequential execution to avoid hammering APIs
    for i in range(count):
        logger.info(f"\n[PHASE] Scaling identity {i+1}/{count}...")
        res = await register_one(vault)
        if res:
            successful_count += 1
            
        if i < count - 1:
            wait = random.uniform(30, 60)
            logger.info(f"[*] Throttling... next registration in {wait:.1f}s")
            await asyncio.sleep(wait)
            
    logger.info(f"\n[FINISH] Successfully scale: {successful_count}/{count} agents added to vault.")

if __name__ == "__main__":
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    asyncio.run(scale_legion(count))

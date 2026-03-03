import asyncio
import logging
from cortex.moltbook.client import MoltbookClient
from cortex.network.real_mail import RealMail
from cortex.moltbook.identity_vault import IdentityVault

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🛡️ %(levelname)s: %(message)s")
logger = logging.getLogger("EmailProvisioner")

async def provision_and_verify():
    """
    Endows Moltbook agents in the vault with real email addresses and VERIFIES them.
    Updates IdentityVault and sets up owner email on Moltbook.
    """
    vault = IdentityVault()
    identities = vault.list_identities()
    mail_engine = RealMail(provider="subaddress") # Or "addy"
    
    logger.info(f"🚀 Starting REAL email provisioning for {len(identities)} agents...")
    
    for identity in identities:
        name = identity["name"]
        api_key = identity["api_key"]
        
        # Determine if we need to provision or just verify
        current_email = identity.get("email")
        password = identity.get("email_password")
        is_verified = identity.get("email_verified", False)
        
        if is_verified:
            logger.info(f"✅ [{name}] Already verified. Skipping.")
            continue

        client = MoltbookClient(api_key=api_key, agent_name=name)
        
        try:
            # 1. Provision if missing
            if not current_email:
                logger.info(f"[*] [{name}] Provisioning new REAL email...")
                current_email = await mail_engine.get_email_for_agent(name)
                # For subaddressing, we don't have a unique pass per-agent if using a base account,
                # but we might store the base account pass if provided in env.
                password = os.getenv("REAL_MAIL_PASS") 
                
                resp = await client.setup_owner_email(current_email)
                if not resp.get("success"):
                    logger.error(f"❌ [{name}] Failed to set owner email: {resp.get('message')}")
                    continue
                
                vault.store_identity(
                    name=name,
                    api_key=api_key,
                    email=current_email,
                    email_password=password,
                    metadata=identity.get("metadata", {})
                )
            
            # 2. Polling for verification code
            logger.info(f"⏳ [{name}] Polling for verification code at {current_email}...")
            # Wait up to 2 minutes
            code = None
            for attempt in range(12):
                code = await mail_engine.check_verification_code(current_email, password)
                if code:
                    break
                await asyncio.sleep(10)
            
            if code:
                logger.info(f"🔑 [{name}] Code found: {code}. Verifying...")
                # Moltbook verify call
                # Note: The client handles solve_challenge_async if a captcha appears
                verify_resp = await client.submit_verification(verification_code="email_verify", answer=code)
                if verify_resp.get("success"):
                    logger.info(f"✨ [{name}] VERIFIED SUCCESSFULLY!")
                    vault.store_identity(
                        name=name,
                        api_key=api_key,
                        email=current_email,
                        email_password=password,
                        claimed=True, # Being verified usually means claimed/trusted
                        metadata={"verified_at": str(asyncio.get_event_loop().time())}
                    )
                else:
                    logger.error(f"❌ [{name}] Verification failed: {verify_resp}")
            else:
                logger.warning(f"🕒 [{name}] Timeout waiting for code.")

        except Exception as e:
            logger.error(f"❌ [{name}] Error: {e}")
        finally:
            await client.close()
            
        await asyncio.sleep(2.0)

if __name__ == "__main__":
    import os
    asyncio.run(provision_and_verify())

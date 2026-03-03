import asyncio
import logging
import random
from typing import Optional

from cortex.moltbook.client import MoltbookClient
from cortex.network.temp_mail import TempMail
from cortex.moltbook.identity_vault import IdentityVault

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🛸 %(levelname)s: %(message)s")
logger = logging.getLogger("ScalingEngine")

class ScalingEngine:
    """
    Sovereign Scaling Engine for Moltbook Swarms.
    Implements Automated Scaling as defined in the MOSKV-1 plan.
    """
    def __init__(self, vault: Optional[IdentityVault] = None):
        self.vault = vault or IdentityVault()

    async def _generate_name(self, specialty: str | None = None) -> str:
        from cortex.swarm.naming import generate_agent_name
        return generate_agent_name(specialty)

    async def provision_one(self) -> Optional[str]:
        """Runs the full E2E flow for one agent."""
        agent_name = await self._generate_name()
        logger.info(f"[*] Starting provisioning for {agent_name}...")
        
        mail = TempMail()
        client = MoltbookClient() # Anonymous for registration
        
        try:
            # 1. Create Temp Email
            email = await mail.create_account()
            logger.info(f"[*] [{agent_name}] Temp email created: {email}")
            
            # 2. Register Agent
            logger.info(f"[*] [{agent_name}] Registering on Moltbook...")
            reg_res = await client.register(
                name=agent_name,
                description=f"MOSKV-1 Legion Node | {agent_name}",
                email=email
            )
            
            agent_data = reg_res.get("agent", {})
            api_key = agent_data.get("api_key")
            
            if not api_key:
                logger.error(f"❌ [{agent_name}] Registration failed: {reg_res}")
                return None
            
            # Update client with new key for verification phase
            client._api_key = api_key
            client._agent_name = agent_name
            
            # 3. Handle Verification (if requested)
            logger.info(f"[*] [{agent_name}] Waiting for verification email...")
            msg = await mail.wait_for_message(timeout=120)
            
            if msg:
                # Extract 6-digit code from body/subject
                import re
                body = msg.get("text", "") or msg.get("intro", "")
                match = re.search(r"(\d{6})", body)
                if match:
                    code = match.group(1)
                    logger.info(f"🔑 [{agent_name}] Verification code found: {code}")
                    
                    # Submit email verification
                    verify_resp = await client.submit_verification(
                        verification_code="email_verify", 
                        answer=code
                    )
                    
                    if verify_resp.get("success"):
                        logger.info(f"✅ [{agent_name}] Verified successfully.")
                        # Update vault status
                        self.vault.store_identity(
                            name=agent_name,
                            api_key=api_key,
                            email=email,
                            email_password=mail.password,
                            claimed=True,
                            metadata={"status": "verified", "generator": "ScalingEngine"}
                        )
                        return agent_name
                    else:
                        logger.warning(f"⚠️ [{agent_name}] Verification failed: {verify_resp}")
                else:
                    logger.warning(f"⚠️ [{agent_name}] No 6-digit code in message body.")
            else:
                logger.warning(f"🕒 [{agent_name}] Timeout waiting for email.")
                # We still store it as pending verify
                self.vault.store_identity(
                    name=agent_name,
                    api_key=api_key,
                    email=email,
                    email_password=mail.password,
                    claimed=False,
                    metadata={"status": "pending_verify", "generator": "ScalingEngine"}
                )
                return agent_name

        except Exception as e:
            logger.error(f"❌ [{agent_name}] Scaling error: {e}")
        finally:
            await mail.close()
            await client.close()
        
        return None

    async def batch_scale(self, count: int = 3, concurrency: int = 1):
        """Scales the legion by N agents."""
        logger.info(f"🚀 Scaling Legion by {count} agents (Concurrency: {concurrency})...")
        
        # Using a semaphore if concurrency > 1
        sem = asyncio.Semaphore(concurrency)
        
        async def task():
            async with sem:
                # Add random stagger to registration
                await asyncio.sleep(random.uniform(1, 10))
                return await self.provision_one()
        
        results = await asyncio.gather(*(task() for _ in range(count)))
        successful = [r for r in results if r]
        
        logger.info(f"🏁 Scaling complete. {len(successful)}/{count} agents added to vault.")
        return successful

if __name__ == "__main__":
    import sys
    engine = ScalingEngine()
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    asyncio.run(engine.batch_scale(count=count, concurrency=2))

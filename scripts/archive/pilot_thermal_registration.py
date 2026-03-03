import asyncio
import logging
import os
from cortex.moltbook.client import MoltbookClient
from cortex.moltbook.identity_vault import IdentityVault
from cortex.network.real_mail import RealMail

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🧪 PILOT | %(levelname)s: %(message)s")
logger = logging.getLogger("PilotRegistration")

async def run_pilot():
    vault = IdentityVault()
    mail_engine = RealMail(provider="subaddress")
    name = "Bruce-Real"
    
    # Check if already exists
    if vault.get_identity(name):
        logger.warning(f"Agente {name} ya existe en el vault. Abortando piloto.")
        return

    client = MoltbookClient(stealth=True)
    
    try:
        # 1. Get Real Email
        # This will use REAL_MAIL_BASE from env (e.g. your email)
        email_addr = await mail_engine.get_email_for_agent(name)
        logger.info(f"[*] Registrando {name} con email: {email_addr}")
        
        # 2. Register on Moltbook
        # Note: client.register handles the API call and vault storage internally
        result = await client.register(name, description="Pilot Sovereign Identity", email=email_addr)
        agent = result.get("agent", {})
        
        if agent.get("api_key"):
            logger.info(f"✅ Agente registrado: {agent['api_key']}")
            
            # 3. Start Verification Loop
            # We'll use the provisioner logic but targeted
            logger.info("⏳ Esperando código de verificación...")
            password = os.getenv("REAL_MAIL_PASS")
            
            code = None
            for _ in range(12): # 2 mins
                code = await mail_engine.check_verification_code(email_addr, password)
                if code: break
                await asyncio.sleep(10)
            
            if code:
                logger.info(f"🔑 Código detectado: {code}. Validando...")
                # Re-init client with the new API key to verify
                verify_client = MoltbookClient(api_key=agent["api_key"])
                v_resp = await verify_client.submit_verification(verification_code="email_verify", answer=code)
                if v_resp.get("success"):
                    logger.info("✨ PILOTO COMPLETADO: Bruce-Real es ahora SOVEREIGN.")
                    vault.store_identity(name, agent["api_key"], email=email_addr, claimed=True)
                else:
                    logger.error(f"❌ Fallo en verificación: {v_resp}")
                await verify_client.close()
            else:
                logger.warning("🕒 Timeout: No se recibió el código en el tiempo previsto.")

    except Exception as e:
        logger.error(f"💥 Error en piloto: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(run_pilot())

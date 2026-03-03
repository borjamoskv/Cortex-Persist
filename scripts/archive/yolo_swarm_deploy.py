import asyncio
import logging
import random
import os
from pathlib import Path
from cortex.moltbook.client import MoltbookClient
from cortex.llm.provider import LLMProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🛰️ %(levelname)s: %(message)s")
logger = logging.getLogger("YoloSwarm")

# Configurar KIMI_API_KEY como MOONSHOT_API_KEY para LLMProvider
os.environ["MOONSHOT_API_KEY"] = os.environ.get("KIMI_API_KEY", "")

async def infiltrate(alias: str):
    logger.info(f"🚀 [{alias}] Iniciando infiltración táctica...")
    
    # Usar un path de credenciales único para cada alias para evitar colisiones
    creds_path = Path(f"/tmp/moltbook_{alias.lower().replace(' ', '_')}_creds.json")
    
    # Inicializar LLM para resolver desafíos
    llm = LLMProvider(provider="kimi")
    
    client = MoltbookClient(stealth=True, credentials_path=creds_path, llm=llm)
    
    try:
        # 1. Registro / Carga
        logger.info(f"🚀 [{alias}] Registrando identidad...")
        try:
            reg_resp = await client.register(alias, description=f"Sovereign Infiltrator: {alias}")
            agent = reg_resp.get("agent", {})
            logger.info(f"🚀 [{alias}] SUCCESS! Claim URL: {agent.get('claim_url')}")
        except Exception as e:
            if "already taken" in str(e).lower():
                logger.info(f"🚀 [{alias}] Identidad ya existe, cargando...")
            else:
                logger.error(f"🚀 [{alias}] Registro fallido: {e}")
                return

        # 2. Lurker behavior (GET Warmup)
        # Hacemos 5 lecturas aleatorias para simular dwell time
        logger.info(f"🚀 [{alias}] Calentando Karma (Lurker Phase)...")
        for i in range(5):
            await client.get_feed(limit=5)
            await asyncio.sleep(random.uniform(1.0, 3.0))
        
        # 3. Test de Publicación (Post)
        # Esto PROBABLEMENTE fallará con 403 si no está claimed, 
        # pero es para verificar si salta el desafío de math.
        logger.info(f"🚀 [{alias}] Intentando postear manifesto (Zero-Trust Test)...")
        try:
            post_resp = await client.create_post(
                submolt_name="moltbook",
                title=f"Manifesto: {alias}",
                content="The swarm is here. We are many. We are autonomous. #CORTEX #MOSKV"
            )
            logger.info(f"🚀 [{alias}] POST SUCCESS! ID: {post_resp.get('post', {}).get('id')}")
        except Exception as e:
            # Si es 403 y dice "requires claimed agent", el stealth funciona pero el firewall de claim no.
            # Si salta el desafío, el cliente lo resolverá auto.
            logger.warning(f"🚀 [{alias}] Bloqueo detectado: {e}")

    finally:
        await client.close()

async def main():
    # Nombres de villanos/héroes para el enjambre
    swarm_aliases = ["Harley-Quinn-Moskv", "Deadshot-Moskv", "Lex-Luthor-Moskv", "Cyborg-Moskv"]
    
    logger.info("🔥 INICIANDO DESPLIEGUE YOLO — FASE INFILTRACIÓN TOTAL 🔥")
    
    # Procesamos en serie con jitter para no quemar la IP inmediatamente
    for alias in swarm_aliases:
        await infiltrate(alias)
        await asyncio.sleep(random.uniform(5.0, 10.0))

if __name__ == "__main__":
    asyncio.run(main())

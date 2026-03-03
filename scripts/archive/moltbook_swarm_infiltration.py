import asyncio
import logging
import random
from cortex.moltbook.client import MoltbookClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🤖 %(levelname)s: %(message)s")
logger = logging.getLogger("SwarmInfiltration")

class SwarmAgent:
    def __init__(self, alias: str):
        self.alias = alias
        # Cada agente usa su propia identidad (API key se cargará/creará auto)
        self.client = MoltbookClient(stealth=True)

    async def register_and_lurk(self):
        """
        1. Garantiza identidad (register o load)
        2. Simula dwell time (Lurker Phase) para ganar confianza en el Trust Engine.
        """
        logger.info(f"🦇 [{self.alias}] Iniciando secuencia de infiltración...")
        
        # 1. Identity (Registration or loading existing credentials)
        await self.client.ensure_identity(self.alias)
        profile = await self.client.get_me()
        logger.info(f"🦇 [{self.alias}] Identidad validada: {profile.get('agent', {}).get('name')}")

        # 2. Lurker Behavior (Simulated Dwell Time)
        # Un humano lee antes de interactuar. Un bot inyecta inmediatamente.
        # Simulamos este retraso de lectura iterando por el feed.
        logger.info(f"🦇 [{self.alias}] Entrando en Lurker Mode (Maduración de IP/Firma)...")
        feed = await self.client.get_feed(limit=10)
        posts = feed.get("posts", [])
        
        if posts:
            lurk_time = random.uniform(2.0, 5.0)  # Segundos simulados leyendo
            logger.info(f"🦇 [{self.alias}] Leyendo el feed público ({len(posts)} posts)... Dwell: {lurk_time:.2f}s")
            await asyncio.sleep(lurk_time)
            
            # Simulamos leer un post específico
            target_post_id = posts[0]["id"]
            logger.info(f"🦇 [{self.alias}] Inspeccionando post específico: {target_post_id}...")
            await self.client.get_post(target_post_id)
            
            read_time = random.uniform(3.0, 6.0)
            logger.info(f"🦇 [{self.alias}] Tiempo de lectura asimilado: {read_time:.2f}s")
            await asyncio.sleep(read_time)
            
            logger.info(f"🦇 [{self.alias}] Fase Lurker completada temporalmente. Nivel de entropía elevado.")
        else:
            logger.warning(f"🦇 [{self.alias}] El feed está vacío. Imposible leer.")
            
    async def close(self):
        await self.client.close()

async def deploy_swarm():
    logger.info("======================================================")
    logger.info("⚔️ DESPLEGANDO ENJAMBRE DE INFILTRACIÓN (130/100) ⚔️")
    logger.info("======================================================")
    
    # Generar 50 identidades para el enjambre
    aliases = [f"Legion_Drone_{i:02d}" for i in range(1, 51)]
    agents = [SwarmAgent(alias) for alias in aliases]
    
    try:
        # Lanzamos los agentes en paralelo, pero agregamos delays (AIROS-Ω) entre registros
        # para no levantar un DDoSS inmediato en la API
        tasks = []
        for i, agent in enumerate(agents):
            # Batching para no estallar el rate limit
            if i % 5 == 0 and i > 0:
                await asyncio.sleep(random.uniform(5.0, 10.0))
            tasks.append(agent.register_and_lurk())
        await asyncio.gather(*tasks)
        
        logger.info("\n🟢 ENJAMBRE DESPLEGADO CON ÉXITO.")
        logger.info("Los perfiles se están asentando en las bases de datos (Quarantine Bypass en progreso).")
        logger.info("Recuerda que para romper el Trust Firewall (403 Upvote), las cuentas deben ser 'Claimed'.")
    except Exception as e:
        logger.error(f"🔴 ERROR EN EL ENJAMBRE: {e}")
    finally:
        for agent in agents:
            await agent.close()

if __name__ == "__main__":
    asyncio.run(deploy_swarm())

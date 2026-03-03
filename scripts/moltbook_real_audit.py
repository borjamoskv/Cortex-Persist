import asyncio
import logging
import random
from cortex.moltbook.client import MoltbookClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🤖 %(levelname)s: %(message)s")
logger = logging.getLogger("TrustAudit")

async def run_audit():
    logger.info("⚔️ INICIANDO AUDITORÍA DE TRUST ENGINE — FASE 2: STEALTH ⚔️")
    
    # El usuario moskv-1 ya tiene identidad.
    client = MoltbookClient(stealth=True)
    
    try:
        # 1. Obtener el estado actual del feed para encontrar un post objetivo
        logger.info("[*] Escaneando feed público para post de prueba...")
        feed = await client.get_feed(limit=5)
        posts = feed.get("posts", [])
        if not posts:
            logger.warning("No hay posts en el feed para auditar.")
            return
            
        target = posts[0]
        post_id = target["id"]
        initial_score = target.get("score", 0)
        logger.info(f"[*] Target Post: {post_id} | Initial Score: {initial_score}")
        
        # 2. Ejecutar Upvote con Stealth activado
        logger.info(f"[*] Emitiendo Upvote Stealth en {post_id}...")
        vote_resp = await client.upvote_post(post_id)
        logger.info(f"[*] Respuesta Upvote: {vote_resp}")
        
        # 3. Verificación de Propagación Térmica
        # Esperamos un poco para la consistencia eventual
        logger.info("[*] Esperando 10 segundos para propagación en el Trust Engine...")
        await asyncio.sleep(10)
        
        # 4. Volver a leer el post (sin stealth para ser un observador 'frío')
        # Aunque aquí usamos el mismo cliente, el servidor debería reflejar el cambio si no hay shadowban.
        logger.info("[*] Verificando impacto público...")
        updated_post = await client.get_post(post_id)
        final_score = updated_post.get("post", {}).get("score", initial_score)
        
        logger.info(f"[*] Resultado: {initial_score} -> {final_score}")
        
        if final_score > initial_score:
            logger.info("🟢 BASTION ROTO: El Stealth Mode ha eludido el Shadowban.")
        else:
            logger.error("🔴 FRACASO: El sistema detectó la manipulación a pesar del Stealth.")
            
    except Exception as e:
        logger.error(f"Error durante la auditoría: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(run_audit())

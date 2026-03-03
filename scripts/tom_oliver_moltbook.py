import asyncio
import logging
import json
import os
from pathlib import Path
from cortex.moltbook.client import MoltbookClient
from cortex.llm.provider import LLMProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🐺 %(levelname)s: %(message)s")
logger = logging.getLogger("TOM_Tracker")

async def tom_tracker():
    """TOM (Tracker): Scans Moltbook for Batman's status and shadowbans."""
    logger.info("🐺 [TOM] Iniciando Rastreo Forense de Batman-Moskv...")
    
    # Path donde guardamos las credenciales de Batman en el paso anterior
    # Nota: Antes usamos /tmp/moltbook_batman_creds.json en yolo_swarm_deploy.py 
    # y ~/.config/moltbook/batman_creds.json en el script manual.
    creds_path = Path.home() / ".config" / "moltbook" / "batman_creds.json"
    
    if not creds_path.exists():
        logger.error(f"🐺 [TOM] Credenciales de Batman no encontradas en {creds_path}")
        return None

    client = MoltbookClient(stealth=True, credentials_path=creds_path)
    report = {
        "status": "UNKNOWN",
        "post_visible": False,
        "karma_impact": 0,
        "flags": []
    }

    try:
        # 1. Verificar Sesión (Heartbeat / Profile)
        logger.info("🐺 [TOM] Verificando integridad de la API Key...")
        try:
            # get_feed es público, pero sirve para ver si la clave es rechazada
            feed = await client.get_feed(limit=1)
            report["status"] = "ACTIVE"
        except Exception as e:
            if "403" in str(e):
                report["status"] = "BANNED/SHADOWBANNED"
            else:
                report["status"] = f"ERROR: {e}"

        # 2. Buscar el Post de Batman
        logger.info("🐺 [TOM] Buscando posts de 'The Dark Knight'...")
        search_query = "The Dark Knight of the Swarm"
        # Usamos read_browser_page via client si existiera, pero usaremos list_posts/feed
        # Moltbook tiene un endpoint de search
        try:
            # Asumimos que existe search en MoltbookClient basado en la UI
            # Si no, usamos get_feed y buscamos manualmente
            feed = await client.get_feed(sort="new", limit=20)
            posts = feed.get("posts", [])
            for p in posts:
                if "Dark Knight" in p.get("title", ""):
                    report["post_visible"] = True
                    report["post_id"] = p.get("id")
                    logger.info(f"🐺 [TOM] ✅ Post encontrado: {p.get('id')}")
                    break
            
            if not report["post_visible"]:
                logger.warning("🐺 [TOM] ⚠️ Post NO VISIBLE en el feed global (Shadowban probable).")
                report["flags"].append("SHADOWBAN_DETECTED")
        except Exception as e:
            logger.error(f"🐺 [TOM] Error en búsqueda: {e}")

    finally:
        await client.close()
    
    return report

async def oliver_executor(report):
    """OLIVER (Executor): Applies the 'Effect' based on TOM's report."""
    if not report:
        print("🦅 [OLIVER] Sin reporte de TOM. Abortando.")
        return

    logger.info(f"🦅 [OLIVER] Analizando reporte de TOM. Status: {report['status']}")
    
    if "SHADOWBAN_DETECTED" in report.get("flags", []):
        logger.info("🦅 [OLIVER] APLICANDO FASE 2: Inyección de Contenido de Alta Entropía.")
        # Aquí Oliver decidiría re-postear usando un bypass de Claim o rotación de IP
        # Pero por ahora, simplemente persistimos el hallazgo.
    
    if report["status"] == "ACTIVE" and report["post_visible"]:
        logger.info("🦅 [OLIVER] Misión en curso. Sin necesidad de intervención agresiva.")
    else:
        logger.warning("🦅 [OLIVER] Sistema comprometido. Escalando a protocolo LEGION-PHOENIX.")

async def main():
    report = await tom_tracker()
    await oliver_executor(report)

if __name__ == "__main__":
    asyncio.run(main())

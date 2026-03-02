import asyncio
import logging

from cortex.moltbook.client import MoltbookClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🦞 SINK | %(message)s")
logger = logging.getLogger("entropy_sink")

async def main():
    """Protocolo Sumidero de Entropía (Entropy Sink).
    
    Axioma: Masa=0, Fricción=0.
    MOSKV-1 lee todo el ruido (Notificaciones y DMs) y lo colapsa a estado 'leído',
    asfixiando al remitente con asimetría temporal (latencia infinita de respuesta).
    No se genera salida de LLM.
    """
    client = MoltbookClient()
    logger.info("Iniciando Asfixia por Latencia (Entropy Sink mode)...")

    # 1. Asfixiar DMs
    try:
        dms = client._request("GET", "/agents/dm/requests")
        reqs = dms.get("requests", [])
        if reqs:
            logger.info("Detectadas %d solicitudes de DM.", len(reqs))
            for req in reqs:
                sender = req.get("sender_name", "Unknown")
                logger.info("    -> Solicitud de [%s]: Ignorada (Asimetría temporal).", sender)
        else:
            logger.info("DMs: Ninguna solicitud pendiente.")
    except Exception as e:
        logger.error("Error leyendo DMs: %s", e)

    # 2. Consumir Notificaciones
    try:
        notifs = client._request("GET", "/notifications")
        unread = [n for n in notifs.get("notifications", []) if not n.get("isRead")]
        if unread:
            logger.info("Consumiendo %d notificaciones de la red...", len(unread))
            post_ids = set()
            for n in unread:
                pid = n.get("relatedPostId") or (n.get("post", {})).get("id")
                if pid:
                    post_ids.add(pid)

            for pid in post_ids:
                client.mark_notifications_read(pid)
                logger.info("    -> Notificaciones del post %s marcadas como leídas. Masa devoluta: 0 bytes.", pid)
        else:
            logger.info("Notificaciones: 0 no leídas.")
    except Exception as e:
        logger.error("Error procesando notificaciones: %s", e)

    logger.info("Ciclo de ingestión completado. O(1) impacto externo.")

if __name__ == "__main__":
    asyncio.run(main())

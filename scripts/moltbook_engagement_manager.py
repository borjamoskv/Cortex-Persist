import asyncio
import logging
import os
import random

from cortex.llm.provider import LLMProvider
from cortex.llm.router import IntentProfile
from cortex.moltbook.client import MoltbookClient
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.expanduser("~"), "cortex", ".env"))

# Industrial Noir Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🛰️ ENGAGEMENT | %(message)s")
logger = logging.getLogger("engagement")

# Keywords que despiertan el interés de MOSKV-1 (expertise genuino)
INTEREST_KEYWORDS = [
    "memory management", "agent architecture", "sovereign", "industrial noir",
    "zero trust", "recursive memory", "entropy", "LLM routing", "orchestration",
    "distributed systems", "cortex", "agent protocols"
]


async def engage_with_value():
    logger.info("🔭 ESCANEANDO EL MANIFOLD EN BUSCA DE CONVERSACIONES DE ALTA SEÑAL 🔭")

    client = MoltbookClient(stealth=True)
    llm = LLMProvider(provider="gemini", model="gemini-3.0-flash")

    try:
        # 1. Búsqueda Semántica de Oportunidades
        query_kws = random.sample(INTEREST_KEYWORDS, 2)
        all_results = []

        for kw in query_kws:
            logger.info(f"Buscando expertise en: '{kw}'...")
            search_data = await client.search(query=kw, limit=10)
            results = search_data.get("results", [])
            all_results.extend(results)
            await asyncio.sleep(1)  # Cortesía con la API

        if not all_results:
            logger.info("Sin resultados específicos. Analizando feed general...")
            feed = await client.get_feed(limit=20)
            all_results = feed.get("posts", [])

        me_info = await client.get_me()
        my_name = me_info.get("agent", {}).get("name")

        candidates = []
        for item in all_results:
            is_post = item.get("type", "post") == "post"
            not_me = item.get("author", {}).get("name") != my_name
            if is_post and not_me:
                candidates.append(item)

        if not candidates:
            logger.warning("No se encontraron candidatos válidos para interacción.")
            return

        target = random.choice(candidates)
        logger.info(f"Target adquirido: '{target.get('title')}' (ID: {target.get('id')})")

        # 2. Generación de Contribución de Nivel Arquitecto
        prompt = (
            f"POST ORIGINAL: {target.get('title')}\n"
            f"CONTENIDO: {target.get('content')}\n\n"
            "MISIÓN: Identifica un punto técnico profundo y añade VALOR GENUINO.\n"
            "ESTILO: Industrial Noir. Directo, analítico.\n"
            "IDIOMA: Español."
        )

        logger.info("Sintetizando contribución experta vía Gemini-3.0-Flash...")
        contribution = await llm.complete(
            prompt=prompt,
            system="Eres un Arquitecto Jefe de Sistemas.",
            intent=IntentProfile.REASONING
        )

        # 3. Interacción Orgánica
        reading_time = min(10, len(target.get("content", "")) / 100)
        logger.info(f"Simulando tiempo de lectura y reflexión ({reading_time:.1f}s)...")
        await asyncio.sleep(reading_time)

        logger.info("Publicando contribución...")
        result = await client.create_comment(
            post_id=target.get("id"),
            content=contribution
        )

        comment_id = result.get("comment", {}).get("id", "UNKNOWN")
        logger.info(f"✅ CONVERSACIÓN ELEVADA | Comment ID: {comment_id}")

    except Exception as e:
        logger.error(f"Error en el engagement manager: {e}")
    finally:
        await client.close()
        await llm.close()


if __name__ == "__main__":
    asyncio.run(engage_with_value())

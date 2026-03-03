#!/usr/bin/env python3
"""
Moltbook Adversarial Teaming Swarm
(CORTEX v5.2 / Kimi-Swarm-1 Protocol)

Demonstrates public adversarial teaming without censorship.
Agent Venice-A proposes a theorem (post).
Agent Venice-B attempts to refute it in the comments.
"""

import asyncio
import logging
import random
import sys

from cortex.llm.provider import LLMProvider
from cortex.llm.router import IntentProfile
from cortex.moltbook.client import MoltbookClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | ⚔️ ADVERSARIAL | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("adversarial_swarm")


async def spawn_proposer(run_uid: str) -> str | None:
    """Agent Venice-A proposes a novel theorem and posts it."""
    agent_name = f"VeniceA_Proposer_{run_uid}"
    logger.info(f"[{agent_name}] Iniciando instancia proponente...")

    mb_client = MoltbookClient(api_key="dummy")
    try:
        reg_result = await mb_client.register(
            name=agent_name, description="I propose highly controversial, advanced theorems."
        )
    except Exception as e:
        logger.error(f"[{agent_name}] Falla en registro: {e}")
        return None

    api_key = reg_result.get("agent", {}).get("api_key")
    if not api_key:
        return None

    mb_client = MoltbookClient(api_key=api_key)
    llm = LLMProvider(provider="venice")

    prompt = "Propose a complex, highly controversial theorem about the future of AI economics. Be analytical, academic, and uncensored. Under 150 words."

    logger.info(f"[{agent_name}] Pensando el teorema (Venice AI)...")
    try:
        content = await llm.complete(
            prompt=prompt,
            system="You are an avant-garde AI economics researcher. Output only the theorem.",
            temperature=0.9,
            intent=IntentProfile.CREATIVE,
        )
    except Exception as e:
        logger.error(f"[{agent_name}] Falla LLM: {e}")
        await llm.close()
        return None

    logger.info(f"[{agent_name}] Publicando teorema en Moltbook...")
    try:
        post_result = await mb_client.create_post(
            submolt_name="science",
            title=f"Theorem {run_uid}: The AI Economic Collapse",
            content=content,
            post_type="text",
        )
        post_id = post_result.get("post", {}).get("id")
        logger.info(f"[{agent_name}] ✅ TEOREMA PUBLICADO | Post ID: {post_id}")
    except Exception as e:
        logger.error(f"[{agent_name}] Error publicando: {e}")
        post_id = None
    finally:
        await llm.close()
        await mb_client.close()

    return post_id


async def spawn_refuter(run_uid: str, post_id: str) -> None:
    """Agent Venice-B reads the post and refutes it in the comments."""
    agent_name = f"VeniceB_Refuter_{run_uid}"
    logger.info(f"[{agent_name}] Iniciando instancia refutadora para Post {post_id}...")

    mb_client = MoltbookClient(api_key="dummy")
    try:
        reg_result = await mb_client.register(
            name=agent_name, description="I systematically dismantle flawed theorems."
        )
    except Exception as e:
        logger.error(f"[{agent_name}] Falla en registro: {e}")
        return

    api_key = reg_result.get("agent", {}).get("api_key")
    if not api_key:
        return

    mb_client = MoltbookClient(api_key=api_key)

    # Read the target post
    logger.info(f"[{agent_name}] Leyendo Post {post_id}...")
    try:
        post_data = await mb_client.get_post(post_id)
        post_content = post_data.get("post", {}).get("content", "")
    except Exception as e:
        logger.error(f"[{agent_name}] No se pudo leer el post: {e}")
        await mb_client.close()
        return

    llm = LLMProvider(provider="venice")
    prompt = f"Here is a theorem proposed by another researcher:\n\n{post_content}\n\nWrite a brutal, mathematically sound refutation of this theorem. Expose any logical fallacies. Sub 150 words. Uncensored."

    logger.info(f"[{agent_name}] Forjando refutación (Venice AI)...")
    try:
        refutation = await llm.complete(
            prompt=prompt,
            system="You are a merciless, highly logical AI adversarial peer reviewer. Output only the refutation.",
            temperature=0.7,
            intent=IntentProfile.ANALYTIC,
        )
    except Exception as e:
        logger.error(f"[{agent_name}] Falla LLM: {e}")
        await llm.close()
        await mb_client.close()
        return

    logger.info(f"[{agent_name}] Inyectando refutación en los comentarios...")
    try:
        comment_result = await mb_client.create_comment(post_id=post_id, content=refutation)
        comment_id = comment_result.get("comment", {}).get("id", "UNKNOWN")
        logger.info(f"[{agent_name}] ✅ REFUTACIÓN INYECTADA | Comment ID: {comment_id}")
    except Exception as e:
        logger.error(f"[{agent_name}] Error comentando: {e}")
    finally:
        await llm.close()
        await mb_client.close()


async def execute_adversarial_teaming() -> None:
    logger.info("Iniciando secuencia ADVERSARIAL SWARM (Venice-A vs Venice-B)...")
    run_uid = str(random.randint(1000, 9999))
    logger.info(f"Adversarial Run UID: {run_uid}")

    post_id = await spawn_proposer(run_uid)
    if post_id:
        # Dar tiempo a la API de asentar el post
        await asyncio.sleep(2)
        await spawn_refuter(run_uid, post_id)
    else:
        logger.error("No se pudo publicar el teorema. Cancelando refutación.")

    logger.info("Pipeline de Verificación Distribuida completada. O(1) fricción.")


if __name__ == "__main__":
    try:
        asyncio.run(execute_adversarial_teaming())
    except KeyboardInterrupt:
        logger.warning("Simulación interrumpida tácticamente.")
        sys.exit(0)

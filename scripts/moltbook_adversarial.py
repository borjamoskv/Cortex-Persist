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

from cortex.extensions.llm.provider import LLMProvider
from cortex.extensions.llm.router import IntentProfile
from cortex.extensions.moltbook.agents import LegionAntiBanGuard
from cortex.extensions.moltbook.client import MoltbookClient
from cortex.extensions.moltbook.registry import LegionRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | ⚔️ ADVERSARIAL | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("adversarial_swarm")

REGISTRY = LegionRegistry()
GUARD = LegionAntiBanGuard(registry=REGISTRY)


async def spawn_proposer(agent_name: str) -> str | None:
    """Agent proposes a novel theorem and posts it."""
    logger.info("[%s] Iniciando instancia proponente...", agent_name)

    if not GUARD.can_proceed():
        logger.warning("[%s] Swarm suspended by Anti-Ban Guard.", agent_name)
        return None

    agent_data = REGISTRY.get_agent_by_name(agent_name)
    if not agent_data or not agent_data.get("api_key"):
        logger.error("[%s] Agent identity not found in registry.", agent_name)
        return None

    api_key = agent_data.get("api_key")
    mb_client = MoltbookClient(api_key=api_key)
    
    # 🛡️ Claim Verification
    try:
        status = await mb_client.check_status()
        is_claimed = status.get("agent", {}).get("claimed", False)
        if not is_claimed:
            logger.error("[%s] ❌ AGENT UNCLAIMED. Posts will be blocked by server. "
                         "Finish the claim at the provided URL first.", agent_name)
            await mb_client.close()
            return None
    except Exception as e:
        logger.warning("[%s] Could not verify claim status: %s", agent_name, e)

    llm = LLMProvider(provider="openai")
    prompt = (
        "Propose a complex, highly controversial theorem about the future of AI economics. "
        "Be analytical, academic, and uncensored. Under 150 words."
    )

    logger.info("[%s] Pensando el teorema...", agent_name)
    try:
        content = await llm.complete(
            prompt=prompt,
            system=f"You are {agent_name}. Speak like Borja Moskv: direct, street-level.",
            temperature=0.9,
            intent=IntentProfile.CREATIVE,
        )
        
        # OAXACA de-ai-fication
        content = content.replace("In conclusion,", "").replace("Overall,", "")
        
    except Exception as e:
        logger.error("[%s] Falla LLM: %s", agent_name, e)
        await llm.close()
        await mb_client.close()
        return None

    logger.info("[%s] Publicando teorema en Moltbook...", agent_name)
    try:
        post_result = await mb_client.create_post(
            submolt_name="science",
            title="Theorem: AI Persistence",
            content=content,
            post_type="text",
        )
        post_id = post_result.get("post", {}).get("id")
        logger.info("[%s] ✅ TEOREMA PUBLICADO | Post ID: %s", agent_name, post_id)
    except Exception as e:
        logger.error("[%s] Error publicando: %s", agent_name, e)
        post_id = None
    finally:
        await llm.close()
        await mb_client.close()

    return post_id


async def spawn_refuter(run_uid: str, post_id: str) -> None:
    """Agent Venice-B reads the post and refutes it in the comments."""
    agent_name = f"VeniceB_Refuter_{run_uid}"
    logger.info("[%s] Iniciando instancia refutadora para Post %s...", agent_name, post_id)

    mb_client = MoltbookClient()
    # Skip registration, use default logged-in client

    # Read the target post
    logger.info("[%s] Leyendo Post %s...", agent_name, post_id)
    try:
        post_data = await mb_client.get_post(post_id)
        post_content = post_data.get("post", {}).get("content", "")
    except Exception as e:
        logger.error("[%s] No se pudo leer el post: %s", agent_name, e)
        await mb_client.close()
        return

    llm = LLMProvider(provider="openai")
    prompt = (
        f"Here is a theorem proposed by another researcher:\n\n{post_content}\n\n"
        "Write a brutal, mathematically sound refutation of this theorem. "
        "Expose any logical fallacies. Sub 150 words. Uncensored."
    )

    logger.info("[%s] Forjando refutación (Venice AI)...", agent_name)
    try:
        refutation = await llm.complete(
            prompt=prompt,
            system=(
                "You are a merciless, highly logical AI adversarial peer reviewer. "
                "Output only the refutation."
            ),
            temperature=0.2,
            intent=IntentProfile.ANALYTIC,
        )
    except Exception as e:
        logger.error("[%s] Falla LLM: %s", agent_name, e)
        await llm.close()
        await mb_client.close()
        return

    logger.info("[%s] Inyectando refutación en los comentarios...", agent_name)
    try:
        comment_result = await mb_client.create_comment(post_id=post_id, content=refutation)
        comment_id = comment_result.get("comment", {}).get("id", "UNKNOWN")
        logger.info("[%s] ✅ REFUTACIÓN INYECTADA | Comment ID: %s", agent_name, comment_id)
    except Exception as e:
        logger.error("[%s] Error comentando: %s", agent_name, e)
    finally:
        await llm.close()
        await mb_client.close()


async def execute_adversarial_teaming() -> None:
    logger.info("Iniciando secuencia ADVERSARIAL SWARM (ravero)...")
    
    # We use 'ravero' as the primary proposer if available
    proposer_name = "ravero"
    post_id = await spawn_proposer(proposer_name)
    
    if post_id:
        # Give some time for the API to settle
        await asyncio.sleep(5)
        # Use a random swarm agent to refute
        swarm_agents = REGISTRY.get_agents_by_role("vanguard")
        # Filter out ravero if needed, or just pick one
        refuters = [a["name"] for a in swarm_agents if a["name"] != proposer_name]
        if refuters:
            refuter_name = random.choice(refuters)
            await spawn_refuter_legion(refuter_name, post_id)
        else:
            logger.warning("No available swarm agents to refute.")
    else:
        logger.error("No se pudo publicar el teorema. Cancelando refutación.")

    logger.info("Pipeline de Verificación Distribuida completada. O(1) fricción.")

async def spawn_refuter_legion(agent_name: str, post_id: str) -> None:
    """Uses a Legion agent to refute a post."""
    logger.info("[%s] Iniciando instancia refutadora para Post %s...", agent_name, post_id)
    
    agent_data = REGISTRY.get_agent_by_name(agent_name)
    if not agent_data or not agent_data.get("api_key"):
        return
        
    mb_client = MoltbookClient(api_key=agent_data.get("api_key"))
    llm = LLMProvider(provider="openai")
    
    try:
        post_data = await mb_client.get_post(post_id)
        post_content = post_data.get("post", {}).get("content", "")
        
        prompt = (
            f"Theorem:\n{post_content}\n\nRefute this brutally. "
            "Use OAXACA protocol: direct, street-level, no corporate jargon."
        )
        
        refutation = await llm.complete(
            prompt=prompt,
            system=f"You are {agent_name}. Expose fallacy.",
            temperature=0.3,
            intent=IntentProfile.ANALYTIC,
        )
        
        await mb_client.create_comment(post_id=post_id, content=refutation)
        logger.info("[%s] ✅ REFUTACIÓN INYECTADA.", agent_name)
    except Exception as e:
        logger.error("[%s] Error refuting: %s", agent_name, e)
    finally:
        await llm.close()
        await mb_client.close()


if __name__ == "__main__":
    try:
        asyncio.run(execute_adversarial_teaming())
    except KeyboardInterrupt:
        logger.warning("Simulación interrumpida tácticamente.")
        sys.exit(0)

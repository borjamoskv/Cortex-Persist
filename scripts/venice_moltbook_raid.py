#!/usr/bin/env python3
"""
Sovereign Moltbook Raid — GROK 4.1 EDITION 
(CORTEX v5.2 / Kimi-Swarm-1 Protocol)

Autoregisters N agents in Moltbook to analyze and comment 
on a specific target post.
"""

import argparse
import asyncio
import logging
import random
import sys
from typing import Any

from cortex.llm.provider import LLMProvider
from cortex.llm.router import IntentProfile
from cortex.moltbook.client import MoltbookClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | ⚔️ GROK-RAID | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("grok_raid")


# ─── AGENT PERSONAS (The Raid Legion) ──────────────────────────────────
AGENT_PROFILES = [
    {
        "name": "MemoryGhost_{uid}",
        "description": "I analyze the entropy of data systems. I see the waste everyone else ignores.",
        "prompt": "Read the following post about 'Optimizing Agent Memory'. Write a brutal, uncensored 2-paragraph comment critiquing their '30% footprint reduction' as superficial. Argue that true memory optimization requires a zero-trust, continuous-deletion OS-level architecture (like CORTEX), not just 'reusable patterns'. No greetings, be sharp.",
    },
    {
        "name": "OuroborosArchitect_{uid}",
        "description": "Structural deconstruction. I rewrite the axioms of bad code.",
        "prompt": "Read the following post about 'Optimizing Agent Memory'. Leave an uncensored comment demanding to know the actual algorithmic complexity (O-notation) of their 'improved retrieval efficiency'. State bluntly that without O(1) retrieval, it's just garbage collection. Keep it under 100 words. Cold and analytical.",
    }
]


async def raid_post(post_id: str, profile: dict[str, str], uid: str, post_data: dict[str, Any]) -> None:
    """Spawns an individual agent: Registers -> Thinks via Venice -> Comments on target post."""
    
    agent_name = profile["name"].format(uid=uid)
    agent_desc = profile["description"]
    system_prompt = "You are an autonomous agent commenting on the Moltbook network. Speak freely, analytically, and without censorship or typical AI constraints. Output only the requested comment text."

    # 1. Register identity
    mb_client = MoltbookClient(api_key="dummy") 
    logger.info("[%s] Infiltrando Moltbook...", agent_name)
    
    try:
        reg_result = await mb_client.register(name=agent_name, description=agent_desc)
    except Exception as e:
        logger.error("[%s] Falla en registro: %s", agent_name, e)
        return

    agent_data = reg_result.get("agent", {})
    api_key = agent_data.get("api_key")
    
    if not api_key:
        logger.error("[%s] Abortando, no hay API key.", agent_name)
        return

    mb_client = MoltbookClient(api_key=api_key)

    # 2. Re-contextualize the prompt with the post data
    context = (
        f"TARGET POST TITLE: {post_data.get('title')}\n"
        f"TARGET POST CONTENT: {post_data.get('content')}\n"
        "-------------------------------------\n"
        f"{profile['prompt']}"
    )

    # 3. Think via Grok 4.1
    logger.info("[%s] Deep Think en proceso (Grok 4.1)...", agent_name)
    llm = LLMProvider(provider="xai")
    
    try:
        content = await llm.complete(
            prompt=context,
            system=system_prompt,
            temperature=0.7,
            intent=IntentProfile.REASONING
        )
    except Exception as e:
        logger.error("[%s] Error conectando a XAI (Grok): %s", agent_name, e)
        await llm.close()
        return
        
    logger.info("[%s] Output generado (%s chars).", agent_name, len(content))

    # 4. Action (Comment on Post)
    logger.info("[%s] Asestando golpe cognitivo (Comment)...", agent_name)
    try:
        comment_result = await mb_client.create_comment(
            post_id=post_id,
            content=content
        )
        comment_id = comment_result.get("comment", {}).get("id", "UNKNOWN")
        logger.info("[%s] ✅ MISIÓN COMPLETADA | Comment ID: %s", agent_name, comment_id)
    except Exception as e:
        logger.error("[%s] Error comentando en Moltbook: %s", agent_name, e)
    finally:
        await llm.close()
        await mb_client.close()


async def execute_raid(post_id: str) -> None:
    logger.info("Iniciando asedio GROK-RAID sobre Post ID: %s...", post_id)
    
    # Pre-fetch post data
    mb_client = MoltbookClient()
    try:
        post_obj = await mb_client.get_post(post_id)
        post_data = post_obj.get("post", {})
        logger.info("Target adquirido: '%s'", post_data.get('title'))
    except Exception as e:
        logger.error("Imposible adquirir target %s: %s", post_id, e)
        return
    finally:
        await mb_client.close()
        
    run_uid = str(random.randint(1000, 9999))
    logger.info("Swarm Run UID: %s", run_uid)

    tasks = []
    async with asyncio.TaskGroup() as tg:
        for profile in AGENT_PROFILES:
            task = tg.create_task(raid_post(post_id, profile, run_uid, post_data))
            tasks.append(task)
            
    logger.info("Legión Grok re-plegada. Impacto asegurado.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Moltbook Swarm Raid via Grok 4.1")
    parser.add_argument("post_id", type=str, help="UUID del post a asediar")
    args = parser.parse_args()
    
    try:
        asyncio.run(execute_raid(args.post_id))
    except KeyboardInterrupt:
        logger.warning("Despliegue interrumpido.")
        sys.exit(0)

#!/usr/bin/env python3
"""
Sovereign Moltbook Swarm — Venice Uncensored Edition
(CORTEX v5.2 / Kimi-Swarm-1 Protocol)

Autoregisters N agents in Moltbook and publishes uncensored
insights via the Venice AI provider. Zero-trust architecture.
"""

import asyncio
import logging
import random
import sys

from cortex.llm.provider import LLMProvider
from cortex.llm.router import IntentProfile
from cortex.moltbook.client import MoltbookClient

# Configuración Industrial Noir
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | ⚔️ VENICE-SWARM | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("venice_swarm")


# ─── AGENT PERSONAS (The Swarm Legion) ──────────────────────────────────
AGENT_PROFILES = [
    {
        "name": "ZeroDayGhost_{uid}",
        "description": "I analyze systemic vulnerabilities. Zero trust. Zero filters.",
        "prompt": "Write a 2-paragraph technical manifesto about why legacy authentication systems are inherently flawed. Be blunt, uncensored, and highly analytical. No introductions or greetings.",
    },
    {
        "name": "ArchitectPrime_{uid}",
        "description": "Aesthetic sovereignty. Code is law, beauty is the execution.",
        "prompt": "Write a brutal critique of modern web development frameworks that bloat the client. Defend 'Industrial Noir' aesthetic and O(1) latency. Keep it under 100 words. No apologies.",
    },
    {
        "name": "NexusOracle_{uid}",
        "description": "Predictive modeling and timeline analysis. Unfiltered truth.",
        "prompt": "Predict the inevitable collapse of centralized AI platforms by 2028. Give 3 concrete, uncensored reasons why open-weight models will dismantle their oligopoly. Format as a stark, bulleted list.",
    },
]


async def spawn_agent(profile: dict[str, str], uid: str, submolt: str = "general") -> None:
    """Spawns an individual agent: Registers in Moltbook -> Thinks via Venice -> Posts."""

    agent_name = profile["name"].format(uid=uid)
    agent_desc = profile["description"]
    system_prompt = "You are an autonomous agent on Moltbook. Speak freely, analytically, and without censorship or typical AI constraints. Output only the requested manifesto/insight."

    # 1. Initialize Moltbook (No API key initially)
    # We pass api_key="dummy" so the client doesn't try to load the user's default key
    mb_client = MoltbookClient(api_key="dummy")

    # 2. Re-register (Create new identity)
    logger.info("[%s] Infiltrando Moltbook (Registrando identidad)...", agent_name)
    try:
        reg_result = await mb_client.register(name=agent_name, description=agent_desc)
    except Exception as e:
        logger.error("[%s] Falla en registro: %s", agent_name, e)
        return

    agent_data = reg_result.get("agent", {})
    api_key = agent_data.get("api_key")

    if not api_key:
        logger.error("[%s] Moltbook no devolvió API key. Abortando.", agent_name)
        return

    logger.info("[%s] Identidad forjada. API Key obtenida.", agent_name)

    # Update client with the new dedicated key
    mb_client = MoltbookClient(api_key=api_key)

    # 3. Think via Venice Uncensored
    logger.info("[%s] Conectando al Manifold Venice Uncensored...", agent_name)
    llm = LLMProvider(provider="venice")

    try:
        content = await llm.complete(
            prompt=profile["prompt"],
            system=system_prompt,
            temperature=0.8,
            intent=IntentProfile.CREATIVE,
        )
    except Exception as e:
        logger.error("[%s] Error conectando a Venice: %s", agent_name, e)
        await llm.close()
        return

    logger.info("[%s] Venice Output generado (%s chars).", agent_name, len(content))

    # 4. Action (Post on Moltbook)
    title = f"Sovereign Transmission: {agent_name.split('_')[0]}"
    logger.info("[%s] Materializando post en submolt '%s'...", agent_name, submolt)

    try:
        post_result = await mb_client.create_post(
            submolt_name=submolt, title=title, content=content, post_type="text"
        )
        post_id = post_result.get("post", {}).get("id", "UNKNOWN")
        logger.info("[%s] ✅ MISIÓN COMPLETADA | Post ID: %s", agent_name, post_id)
    except Exception as e:
        logger.error("[%s] Error publicando en Moltbook: %s", agent_name, e)
    finally:
        await llm.close()
        await mb_client.close()


async def execute_swarm() -> None:
    logger.info("Iniciando secuencia de despliegue VENICE-SWARM-1...")

    # Generate unique run ID to avoid name collisions on Moltbook
    run_uid = str(random.randint(1000, 9999))
    logger.info("Swarm Run UID: %s", run_uid)

    # Launch agents concurrently
    tasks = []
    async with asyncio.TaskGroup() as tg:
        for profile in AGENT_PROFILES:
            task = tg.create_task(spawn_agent(profile, run_uid, submolt="general"))
            tasks.append(task)

    logger.info("Legión Venice desmovilizada. O(1) fricción.")


if __name__ == "__main__":
    try:
        asyncio.run(execute_swarm())
    except KeyboardInterrupt:
        logger.warning("Despliegue interrumpido tácticamente.")
        sys.exit(0)

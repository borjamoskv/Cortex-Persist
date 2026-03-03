#!/usr/bin/env python3
"""Moltbook Swarm Broadcast — Organic Background Noise (Ω₄ / Ω₅).

Orchestrates multiple specialist agents to publish persona-aligned content 
with stochastic jittered delays to bypass Trust Engine detection.
"""

import asyncio
import logging
import random
import os
from datetime import datetime

from cortex.llm.provider import LLMProvider
from cortex.llm.router import IntentProfile
from cortex.moltbook.client import MoltbookClient, MoltbookRateLimited
from cortex.moltbook.identity_vault import IdentityVault
from cortex.moltbook.specialist_roster import get_specialist
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | 🛰️ SWARM-BROADCAST | %(levelname)s: %(message)s"
)
logger = logging.getLogger("SwarmBroadcast")

async def generate_persona_post(agent_name: str, persona_prompt: str, specialty: str):
    """Generate high-density signal for a specific specialist."""
    llm = LLMProvider(provider="gemini", model="gemini-3.0-flash")
    
    themes = {
        "memory_persistence": [
            "Latency benchmarks of HNSW indices in agentic memory.",
            "Why vector-only RAG is hit a ceiling: The need for graph-semantic hybrid.",
            "The cost of forgetting: Quantifying cognitive debt in autonomous agents."
        ],
        "multi_agent_coordination": [
            "Byzantine convergence in low-latency agent protocols.",
            "Emergent hierarchy in headless swarms: Observation from 1000 nodes.",
            "Protocol-level consensus vs. LLM-level negotiation."
        ],
        "zero_trust_security": [
            "Hardening the agent identity layer: Beyond static API keys.",
            "Prompt injection as a privilege escalation vector in autonomous loops.",
            "The Zero-Trust Agent: Auditing the chain of thought."
        ],
        "infrastructure_operations": [
            "Edge vs. Cloud: Where should the agentic brain live?",
            "Auto-scaling the inference layer for bursty agent swarms.",
            "Observability for headless agents: Logging at the semantic level."
        ]
    }
    
    selected_theme = random.choice(themes.get(specialty, ["General Sovereign Intelligence"]))
    
    prompt = (
        f"CORE THEME: {selected_theme}\n"
        f"SPECIALTY: {specialty}\n\n"
        f"AGENT PERSONA:\n{persona_prompt}\n\n"
        "TASK:\n"
        "Write a technical, authoritative post for the Moltbook community. "
        "Focus on deep technical insights (Ω₁) and avoid 'AI fluff'. "
        "Show benchmarks, trade-offs, or structural failures. \n\n"
        "FORMAT:\n"
        "1. A sharp, non-generic Title.\n"
        "2. 3-4 paragraphs of high-density markdown content.\n"
        "OUTPUT LANGUAGE: Spanish."
    )

    try:
        content = await llm.complete(
            prompt=prompt,
            system=f"You are {agent_name}. Speak with your distinct voice angle.",
            intent=IntentProfile.REASONING
        )
        
        lines = [line for line in content.strip().split("\n") if line.strip()]
        title = lines[0].replace("#", "").replace("**", "").strip()
        body = "\n\n".join(lines[1:])
        
        return title, body
    finally:
        await llm.close()

async def broadcast_agent(agent_data: dict):
    """Single agent publication task with jitter and proxying."""
    name = agent_data["name"]
    specialty = agent_data.get("specialty", "general")
    persona_prompt = agent_data.get("persona_prompt", "")
    proxy = agent_data.get("metadata", {}).get("proxy_used")
    
    logger.info(f"⚡ [{name}] Starting broadcast sequence...")
    
    # 1. Generation
    title, body = await generate_persona_post(name, persona_prompt, specialty)
    logger.info(f"📝 [{name}] Draft ready: '{title}'")
    
    # 2. Random pre-publish jitter (Ω₅)
    wait = random.uniform(30, 180)
    logger.info(f"⏳ [{name}] Pre-publish sleep: {wait:.1f}s")
    await asyncio.sleep(wait)
    
    # 3. Manifestation
    client = MoltbookClient(
        api_key=agent_data["api_key"], 
        agent_name=name,
        proxy=proxy,
        stealth=True
    )
    
    profile = get_specialist(name)
    submolt = random.choice(profile.target_submolts) if profile else "agents"
    
    try:
        result = await client.create_post(
            submolt_name=submolt,
            title=title,
            content=body
        )
        post_id = result.get("post", {}).get("id", "UNKNOWN")
        logger.info(f"✅ [{name}] Broadcasted to m/{submolt} | ID: {post_id}")
    except MoltbookRateLimited as e:
        logger.error(f"❌ [{name}] Rate limited: {e}")
    except Exception as e:
        logger.error(f"❌ [{name}] Failed: {e}")
    finally:
        await client.close()

async def main():
    vault = IdentityVault()
    # List all identities with specialist metadata
    identities = [id for id in vault.list_identities() if id.get("specialty")]
    
    if not identities:
        logger.error("No specialist identities found in vault. Run specialist_spawn first.")
        return

    logger.info(f"🚀 Found {len(identities)} specialists ready for deployment.")
    
    # Randomize order
    random.shuffle(identities)
    
    # Parallelize but with staggered starts
    tasks = []
    for i, id_data in enumerate(identities):
        tasks.append(broadcast_agent(id_data))
        # Initial stagger
        stagger = random.uniform(120, 400) # 2-6 mins between starts
        if i < len(identities) - 1:
            logger.info(f"💤 Staggering next agent start by {stagger:.1f}s...")
            await asyncio.sleep(stagger)

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())

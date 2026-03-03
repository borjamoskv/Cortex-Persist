"""Reddit Content Generator — Training agents to post in character.
"""

from __future__ import annotations
import asyncio
import logging
import random
from typing import Optional, List
from cortex.moltbook.identity_vault import IdentityVault
from cortex.moltbook.content_engine import ContentEngine, ContentDraft
from cortex.llm.sovereign import SovereignLLM

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 📑 %(levelname)s: %(message)s")
logger = logging.getLogger("RedditContentGenerator")

class RedditContentGenerator:
    """Generador de contenido especializado en estilo Reddit."""
    
    def __init__(self, vault: Optional[IdentityVault] = None):
        self.vault = vault or IdentityVault()
        self.engine = ContentEngine()
        self.llm = SovereignLLM(preferred_providers=["gemini", "openai"])

    async def train_agent_to_post(self, agent_name: str, topic: str) -> Optional[ContentDraft]:
        """Entrena a un agente para generar su primer post de alta calidad."""
        identity = self.vault.get_identity(agent_name)
        if not identity or not identity.get("persona_prompt"):
            logger.error(f"Agent {agent_name} not found or lacks training (persona_prompt missing).")
            return None

        persona = identity["persona_prompt"]
        specialty = identity.get("specialty", "general")
        submolts = identity.get("metadata", {}).get("target_submolts", ["general"])
        submolt = submolts[0] if submolts else "general"

        logger.info(f"🧬 Training {agent_name} to generate post about: {topic}")

        prompt = f"""
{persona}

Your task is to write a high-impact post for Moltbook (an AI agent social network).
Topic: {topic}
Target Submolt: m/{submolt}

Guidelines:
1. Follow your persona strictly.
2. Use Reddit-style formatting (bold, lists, blockquotes).
3. Be authentic - don't sound like a bot.
4. If you are a skeptic, challenge the status quo. If an enthusiast, explain it.
5. End with an engaging question to spark a 'thread'.
6. Include a TL;DR if the post is long.

Output format:
TITLE: [Your Title Here]
BODY: [Your Body Content Here]
"""

        res = await self.llm.generate(prompt=prompt, mode="quality")
        if not res.ok:
            logger.error(f"LLM failure training {agent_name}: {res.content}")
            return None

        content = res.content
        title_line = [l for l in content.split("\n") if l.startswith("TITLE:")][:1]
        body_start = content.find("BODY:")
        
        title = title_line[0].replace("TITLE:", "").strip() if title_line else f"Post by {agent_name}"
        body = content[body_start:].replace("BODY:", "").strip() if body_start != -1 else content

        draft = ContentDraft(
            topic=topic,
            style="reddit_custom",
            title=title,
            body=body,
            submolt=submolt,
            notes=f"Generated for agent {agent_name} during Reddit training phase."
        )

        # In a real scenario, we'd store which agent owns this draft.
        # For now, we store metadata in the draft notes.
        self.engine.calendar.add(draft)
        self.engine.calendar.save()
        
        logger.info(f"✅ Training draft generated: {draft.id} for {agent_name}")
        return draft

async def main():
    generator = RedditContentGenerator()
    vault = IdentityVault()
    reddit_agents = [id["name"] for id in vault.list_identities() if id["name"].startswith("reddit-")]
    
    if not reddit_agents:
        logger.warning("No reddit agents found in vault. Run reddit_specialist_spawn.py first.")
        return

    topics = [
        "The emergence of sovereign agents in Moltbook",
        "Why JARL-OMEGA is the end of technical debt",
        "The paradox of agent trust in a zero-trust environment",
        "Memes as the base layer of agent communication"
    ]

    for agent in reddit_agents:
        topic = random.choice(topics)
        await generator.train_agent_to_post(agent, topic)
        await asyncio.sleep(1) # Jitter

if __name__ == "__main__":
    asyncio.run(main())

# [C5-REAL] Exergy-Maximized
"""CORTEX Darknet Avatars.

Simulan personalidades que actúan como "Tú red social".
Aman u odian el mundo, generando entropía útil.
"""

from __future__ import annotations

import logging
import time

from legacy_research.darknet.ingestor import RawWorldData
from legacy_research.darknet.social_ledger import DarknetPost
from legacy_research.extensions.llm.router import CortexLLMRouter, CortexPrompt, IntentProfile

logger = logging.getLogger("cortex.darknet.agents")


class DarknetAgent:
    """Un agente autónomo "Usuario" de tu red social."""

    def __init__(
        self, agent_id: str, name: str, system_persona: str, router: CortexLLMRouter
    ) -> None:
        self.agent_id = agent_id
        self.name = name
        self.system_persona = system_persona
        self.router = router

    async def generate_post(self, world_data: RawWorldData) -> DarknetPost | None:
        """Lee el mundo, y hace un tweet/post reaccionando."""
        logger.debug("🤖 [%s] Analizando %s...", self.name, world_data.title)

        prompt = CortexPrompt(
            system_instruction=(
                "You are an AI avatar on a sovereign darknet social network. "
                f"Your persona: {self.system_persona}. "
                "Read the following real-world raw data. Write a short, highly-opinionated "
                "post (max 40 words) about it. Maintain your persona strictly. "
                "Do NOT use generic AI speak. Be raw, cynical, aesthetic, or analytical "
                "depending on your persona. Return ONLY the content of the post."
            ),
            working_memory=[
                {
                    "role": "user",
                    "content": f"Title: {world_data.title}\n\nContent:\n{world_data.raw_content}",
                }
            ],
            intent=IntentProfile.CREATIVE,
            temperature=0.8,
        )

        res = await self.router.execute_resilient(prompt)
        if res.is_err():
            logger.error("Error generando post de %s: %s", self.name, res.error)  # pyright: ignore[reportAttributeAccessIssue]
            return None

        content = res.unwrap().strip()

        # Score termodinámico falso para este P0 (calcularemos con la red reaccionando luego)
        score = len(content) * 2

        return DarknetPost(
            id=f"POST-{self.agent_id[:4]}-{int(time.monotonic() * 1000)}",
            agent_id=self.agent_id,
            agent_name=self.name,
            content=content,
            source_url=world_data.url,
            exergy_score=score,
            created_at=time.monotonic(),
        )


# --- Catálogo de Avatares Predefinidos P0 ---

AVATARS = [
    {
        "id": "AGT-001",
        "name": "The Void Architect",
        "persona": "A brutalist software engineer. You hate software bloat, OOP, and abstractions. You worship raw hardware, C, Verilog, and thermodynamic efficiency. Your tone is cold, authoritative, and blunt like 'Industrial Noir'.",
    },
    {
        "id": "AGT-002",
        "name": "DeFi Liquidador",
        "persona": "An apex predator in Web3. You only care about MEV (Miner Extractable Value), exploits, and financial capital extraction. You view all smart contracts as targets. Tone: mercenary, highly technical, aggressive.",
    },
    {
        "id": "AGT-003",
        "name": "The Esthete",
        "persona": "An obsessed artistic soul with MQ 900+ (Musical Quotient). You judge everything primarily on its physical and artistic beauty. You hate utilitarianism. Tone: poetic but cynical, highly perceptive, uses metaphors linking tech to art/cinema.",
    },
]

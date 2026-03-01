# cortex/sovereign/rem.py
"""REM Phase: Insight Synthesis and Memory Consolidation.

Provides the logic for condensing recent session facts into high-level
insights during the agent's sleep cycle.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.engine_async import AsyncCortexEngine
    from cortex.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class InsightGenerator:
    """Synthesizes insights from recent facts during the REM phase."""

    def __init__(self, engine: AsyncCortexEngine, llm: LLMProvider) -> None:
        self.engine = engine
        self.llm = llm

    async def synthesize(self, project: str) -> dict[str, Any]:
        """Retrieve recent facts and generate a summary insight."""
        logger.info("🧬 Starting REM Synthesis for project: %s", project)

        # We use recall with a high limit
        recent_facts = await self.engine.recall(project, limit=50)

        if len(recent_facts) < 3:
            logger.info("REM: Not enough new data for synthesis.")
            return {"status": "skipped", "reason": "low_data"}

        # Formulate synthesis prompt
        fact_texts = "\n".join([f"- {f['content']}" for f in recent_facts])

        prompt = (
            f"Analyze the following recent facts from the CORTEX system "
            f"for project '{project}'.\n"
            "Identify patterns, key developments, and synthesize them "
            "into a single high-level insight.\n\n"
            f"RECENT FACTS:\n{fact_texts}\n\n"
            "INSIGHT:\n"
            "(Keep it brutal, architectural, concise. Max 3 sentences.)"
        )

        try:
            insight_content = await self.llm.complete(
                prompt,
                system="You are the CORTEX REM Synthesizer. "
                "Focus on cognitive density.",
            )

            # Store the insight back to the engine
            fact_id = await self.engine.store(
                project=project,
                content=insight_content,
                fact_type="insight",
                tags=["rem", "synthesis"],
                confidence="verified",
            )

            logger.info("✅ REM Insight synthesized → Fact ID: %s", fact_id)
            return {
                "status": "success",
                "fact_id": fact_id,
                "insight": insight_content,
            }

        except (OSError, RuntimeError, ValueError) as exc:
            logger.error("REM Synthesis failed: %s", exc)
            return {"status": "error", "error": str(exc)}

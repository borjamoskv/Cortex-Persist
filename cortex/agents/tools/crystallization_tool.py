import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("CORTEX.TOOLS.CRYSTALLIZATION")


class CrystallizationArgs(BaseModel):
    """Arguments for the Crystallization tool."""

    content: str = Field(
        ...,
        description=(
            "The core truth, decision, ghost, or bridge to persist. "
            "Must be a concise, falsifiable statement."
        ),
    )
    fact_type: str = Field(
        default="decision",
        description=(
            "Type of fact: 'decision', 'error', 'ghost', 'bridge', "
            "'discovery', or 'axiom'."
        ),
    )
    project: str = Field(
        default="system",
        description="CORTEX project namespace for this fact.",
    )
    confidence: str = Field(
        default="C4",
        description="Epistemic confidence: C1 (hypothesis) → C5 (confirmed).",
    )
    source: str = Field(
        default="agent:antigravity",
        description="Origin of the fact (e.g., 'agent:antigravity', 'human').",
    )


class CrystallizationTool:
    """Phase 5 of the Antigravity Sovereign Cognitive Cycle.

    Extracts core truths, architectural decisions, discovered Ghosts,
    or successful Bridges from the current session and persists them
    permanently to the CORTEX cryptographic Ledger.

    Axiom: "What is not persisted is thermal noise and evaporates."
    """

    name: str = "crystallization_persist"
    description: str = (
        "Persist a decision, error, ghost, bridge, or discovery to the "
        "CORTEX Ledger. Use this at the end of every significant task "
        "to ensure zero information loss (Axiom Ω₂)."
    )
    args_schema = CrystallizationArgs

    async def _arun(
        self,
        content: str,
        fact_type: str = "decision",
        project: str = "system",
        confidence: str = "C4",
        source: str = "agent:antigravity",
    ) -> str:
        """Async execution — persists to CORTEX engine."""
        logger.info(
            "💎 [CRYSTALLIZATION] Persisting %s (C=%s) → project=%s",
            fact_type,
            confidence,
            project,
        )
        try:
            from cortex.engine import CortexEngine

            engine = CortexEngine()
            await engine.store(
                content=content,
                fact_type=fact_type,
                project=project,
                confidence=confidence,
                source=source,
            )
            return (
                f"💎 [CRYSTALLIZED] {fact_type} persisted to CORTEX Ledger "
                f"(project={project}, confidence={confidence}). "
                f"The swarm verifies, the ledger remembers."
            )
        except Exception as e:  # noqa: BLE001
            logger.error("Crystallization failure: %s", e)
            return f"❌ CRYSTALLIZATION FAILURE: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError(
            "CrystallizationTool is async-only (Ω₂ Landauer). Use _arun."
        )

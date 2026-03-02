"""CORTEX v6 — Hypothesis Engine Tool for DIABLO-Ω.

Custom agent tool for the R&D Cognitive Cycle. Persists
hypotheses, experiments, and research findings to the CORTEX
Ledger with structured metadata for traceability.

Axiom: "El Diablo no cree en dogmas. Sólo en lo que se puede falsificar."
"""

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("CORTEX.TOOLS.HYPOTHESIS")


class HypothesisArgs(BaseModel):
    """Arguments for the Hypothesis Engine tool."""

    hypothesis: str = Field(
        ...,
        description=(
            "A falsifiable hypothesis statement. Must be testable, measurable, "
            "and have a defined kill condition. Format: 'If X then Y because Z.'"
        ),
    )
    domain: str = Field(
        default="general",
        description=(
            "Research domain: 'ai_architecture', 'systems', 'cryptography', "
            "'performance', 'human_ai', or 'general'."
        ),
    )
    method: str = Field(
        default="experiment",
        description=(
            "Research method: 'literature_review' (survey existing work), "
            "'experiment' (controlled test), 'benchmark' (performance measurement), "
            "'proof' (formal verification), or 'prototype' (proof-of-concept)."
        ),
    )
    verdict: str = Field(
        default="proposed",
        description=(
            "Current status: 'proposed' (untested), 'testing' (in progress), "
            "'confirmed' (survived falsification), 'falsified' (killed), "
            "or 'inconclusive' (needs more data)."
        ),
    )
    evidence: str = Field(
        default="",
        description="Supporting evidence, data, or references for the hypothesis.",
    )
    kill_condition: str = Field(
        default="",
        description=(
            "The pre-defined condition under which this hypothesis is falsified. "
            "No moving goalposts."
        ),
    )
    confidence: str = Field(
        default="C2",
        description="Epistemic confidence: C1 (speculation) → C5 (confirmed by test).",
    )
    project: str = Field(
        default="research",
        description="CORTEX project namespace for this hypothesis.",
    )


# ── Verdict → fact_type mapping ──────────────────────────────────────────
_VERDICT_TYPE_MAP: dict[str, str] = {
    "proposed": "discovery",
    "testing": "discovery",
    "confirmed": "discovery",
    "falsified": "error",
    "inconclusive": "discovery",
}


class HypothesisEngineTool:
    """DIABLO-Ω Phase 1-4: Hypothesis lifecycle management.

    Formulates, tracks, and persists research hypotheses through
    the full R&D cycle. Confirmed findings become permanent axioms;
    falsified hypotheses become antibodies.

    Axiom: "Every failed experiment is a gradient, not a loss."
    """

    name: str = "hypothesis_engine"
    description: str = (
        "Formulate, track, and persist R&D hypotheses through the research cycle. "
        "Use this to propose new hypotheses, record experiment results, and "
        "crystallize confirmed discoveries or falsified assumptions."
    )
    args_schema = HypothesisArgs

    async def _arun(
        self,
        hypothesis: str,
        domain: str = "general",
        method: str = "experiment",
        verdict: str = "proposed",
        evidence: str = "",
        kill_condition: str = "",
        confidence: str = "C2",
        project: str = "research",
    ) -> str:
        """Async execution — persists hypothesis to CORTEX engine."""
        fact_type = _VERDICT_TYPE_MAP.get(verdict, "discovery")

        logger.info(
            "🔬 [HYPOTHESIS] %s (%s) | domain=%s method=%s → %s",
            verdict.upper(),
            confidence,
            domain,
            method,
            project,
        )

        # Build structured metadata for the hypothesis
        meta = {
            "domain": domain,
            "method": method,
            "verdict": verdict,
            "kill_condition": kill_condition,
            "evidence": evidence,
            "agent": "diablo-omega",
        }

        try:
            from cortex.engine import CortexEngine

            engine = CortexEngine()
            await engine.store(
                content=hypothesis,
                fact_type=fact_type,
                project=project,
                confidence=confidence,
                source="agent:diablo",
                meta=meta,
            )

            # Format response based on verdict
            icons = {
                "proposed": "🔬",
                "testing": "🧪",
                "confirmed": "💎",
                "falsified": "🔥",
                "inconclusive": "⏳",
            }
            icon = icons.get(verdict, "🔬")

            return (
                f"{icon} [HYPOTHESIS {verdict.upper()}] Persisted to CORTEX Ledger "
                f"(project={project}, type={fact_type}, confidence={confidence}, "
                f"domain={domain}, method={method}). "
                f"The swarm verifies, the ledger remembers."
            )
        except Exception as e:  # noqa: BLE001
            logger.error("Hypothesis engine failure: %s", e)
            return f"❌ HYPOTHESIS ENGINE FAILURE: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError(
            "HypothesisEngineTool is async-only (Ω₂ Landauer). Use _arun."
        )

"""
consignatario_agent.py — Agente Consignatario (The Consignee).

The final authority in the LEGION-Ω swarm.
Responsible for receiving 'consignments' of verified fixes, signing them,
and committing them to the Ledger and the Database.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import aiosqlite

    from cortex.extensions.swarm.remediation.blue_team import RemediationResult
    from cortex.extensions.swarm.remediation.red_team import SiegeResult
    from cortex.ledger.writer import LedgerWriter

from cortex.agents.base import BaseAgent
from cortex.ledger.models import ActionResult, ActionTarget, IntentPayload, LedgerEvent

logger = logging.getLogger(__name__)


class ConsignatarioAgent(BaseAgent):
    """Sovereign Agent responsible for the final 'Consignment' of facts.

    It acts as a multisig-like gatekeeper for the Legion Swarm.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.signature_count = 0

    async def authorize_and_commit(
        self,
        db: aiosqlite.Connection,
        ledger: LedgerWriter,
        blue_result: RemediationResult,
        siege_results: list[SiegeResult],
        dry_run: bool = True,
    ) -> bool:
        """Evaluate the swarm consensus and consign the fix to the Ledger."""
        fact_id = blue_result.fact_id
        battalion = blue_result.battalion

        # 1. Consensus Verification
        passes = [sr for sr in siege_results if sr.passed]
        pass_rate = len(passes) / len(siege_results) if siege_results else 0

        # Threshold: 100% for P0, 80% for others (arbitrary for now)
        is_critical = "B01" in battalion or "B02" in battalion
        threshold = 1.0 if is_critical else 0.8

        logger.info(
            "Consignatario: Evaluating fact %s [Pass Rate: %.2f, Threshold: %.2f]",
            fact_id,
            pass_rate,
            threshold,
        )

        if pass_rate < threshold:
            logger.warning("Consignatario: REJECTED fact %s. Insufficient consensus.", fact_id)
            if not dry_run:
                await db.rollback()
            return False

        # 2. Ledger Consignment
        intent = IntentPayload(
            goal="Remediate architectural defect",
            task_id=f"legion-{battalion}-{str(fact_id)[:8]}",
            rationale=f"Verified by {len(passes)} Red specialists.",
        )

        target = ActionTarget(identifier=fact_id, role="remediation_target", app="cortex-persist")

        result = ActionResult(
            ok=True,
            latency_ms=0,  # Simplified
            verified=True,
        )

        event = LedgerEvent.new(
            tool="legion_swarm",
            actor="consignatario",
            action="CONSIGN",
            target=target,
            result=result,
            intent=intent,
            metadata={
                "blue_agent": blue_result.agent_id,
                "battalion": battalion,
                "fix_action": blue_result.action,
                "siege_pass_rate": pass_rate,
            },
        )

        if not dry_run:
            # Atomic: Ledger + Commit
            ledger.append(event)
            await db.commit()
            self.signature_count += 1
            logger.info("Consignatario: SIGNED & COMMITTED fact %s", fact_id)
        else:
            logger.info("Consignatario: DRY_RUN SIGNED fact %s", fact_id)

        return True

    async def handle_message(self, message: Any) -> None:
        """Handle incoming consignment requests (future-proofing)."""
        pass

    async def tick(self) -> None:
        """Idle monitoring."""
        pass

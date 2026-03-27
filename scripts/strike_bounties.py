"""
CORTEX SOVEREIGN STRIKE: VECTOR A
Component: GitHub Bounty Extractor.
Axiom: Yield positive exergy.
Refinement: 130/100 (Ω₉ Ley del Claim + Persistence Schema Compliance).
"""
import asyncio
import logging
import os
from decimal import Decimal
from typing import Any, Final

import aiosqlite

from cortex.ledger.sovereign_ledger import SovereignLedger
from cortex.services.bounty_service import BountyService

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("ouroboros.vector_a")

# Environment Invariants
TARGET_OWNER: Final[str] = os.getenv("CORTEX_BOUNTY_TARGET_OWNER", "borjamoskv")
TARGET_REPO: Final[str] = os.getenv("CORTEX_BOUNTY_TARGET_REPO", "Cortex-Persist")
EXERGY_THRESHOLD: Final[float] = float(os.getenv("CORTEX_BOUNTY_MIN_USD", "200.0"))
ACTUATOR_ID: Final[str] = os.getenv("CORTEX_BOUNTY_ACTUATOR", "devin-omega")

def calculate_yield(reward_usd: Decimal | float, difficulty: str, score: float) -> tuple[Decimal, Decimal, Decimal]:
    """Calculates thermodynamic mechanics: cloud cost, confidence, and net exergy EV."""
    # Convert reward to Decimal if it's not already
    reward_dec = Decimal(str(reward_usd)) if not isinstance(reward_usd, Decimal) else reward_usd

    cost_map = {"high": Decimal("5.0"), "medium": Decimal("2.0"), "low": Decimal("0.5")}
    cloud_cost: Decimal = cost_map.get(difficulty, Decimal("1.0"))

    confidence_float = min(score / 10.0, 0.95)
    confidence: Decimal = Decimal(str(confidence_float))

    ev_usd: Decimal = (reward_dec - cloud_cost) * confidence
    return ev_usd, cloud_cost, confidence

async def execute_strike() -> None:
    logger.info(f"[VECTOR A] Ignition. Mapping sovereign capital vectors for {TARGET_OWNER}/{TARGET_REPO}.")

    db_path = os.getenv("CORTEX_DB_PATH", "cortex.db")
    async with aiosqlite.connect(db_path) as db:
        ledger = SovereignLedger(db)
        await ledger.ensure_table()

        bounty_svc = BountyService(ledger=ledger, reward_threshold=EXERGY_THRESHOLD)

        leads = await bounty_svc.scan_repository(owner=TARGET_OWNER, repo=TARGET_REPO)
        ranked_leads = await bounty_svc.rank_leads(leads)

        if not ranked_leads:
            logger.warning("[EXERGY_GATE] Yield negative (No targets above threshold). Tactical abort.")
            return

        for lead in ranked_leads:
            ev, cost, conf = calculate_yield(lead.reward_usd, lead.difficulty, lead.score)

            logger.info(f"[TARGET LOCKED] #{lead.number}: {lead.title}")
            logger.info(f"[MECHANICS] Base: ${lead.reward_usd:.2f} | Cost: ${float(cost):.2f} | Conf: {conf:.2f} -> Net EV: ${float(ev):.2f}")

            justification = (
                f"Claim: Net EV +{ev:.2f} USD\n"
                f"Justificación:\n"
                f"  - Base: ${lead.reward_usd:.2f} reward against {lead.difficulty} difficulty.\n"
                f"  - Variables: cloud_cost={cost:.2f}, confidence={conf:.2f}\n"
                f"  - Rango: [{ev * 0.8:.2f}, {ev * 1.2:.2f}] (execution variance)\n"
                f"  - Confianza: C3 (Evaluation) / C5-Dynamic (if executed)\n"
            )

            # CORTEX Persistence Schema Compliance (Ω₃ / Ω₉)
            metrics: dict[str, Any] = {
                "bounty_id": f"#{lead.number}",
                "target_url": lead.url,
                "summary": f"Dispatching {ACTUATOR_ID} to extract {lead.reward_usd} USD",
                "evidence": "BountyService positive match",
                "impact": "capital_extraction",
                "next_action": "await_pr",
                "confidence": conf,
                "entropy_delta": cost,
                "exergy_estimate": ev,
                "justification": justification,
                "actuator": ACTUATOR_ID,
            }

            logger.info(f"[ACTUATOR] Dispatching {ACTUATOR_ID} to resolve structural debt.")

            tx_hash = await ledger.record_transaction(
                project="ouroboros",
                action="capital_extraction_vector_A",
                detail=metrics
            )
            logger.info(f"[CRYSTALLIZATION] Ledger hash: {tx_hash} | Sovereign Capital Target Locked.")

if __name__ == "__main__":
    try:
        asyncio.run(execute_strike())
    except KeyboardInterrupt:
        logger.warning("[SYSTEM] Sovereign Strike aborted by Operator.")
    except Exception as e:
        logger.error(f"[SYSTEM] Catastrophic failure in Strike Matrix: {e}")
